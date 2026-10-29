#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). No target, SSH connection or download is used.
"""talloc and tdb cross builds replay stored Waf answers by default.

The default mode (EMBERBSD_WAF_ANSWERS_MODE=replay) configures with
--cross-answers only: no --cross-execute, no target, no query configuration.
The stored files/cross-answers/PLATFORM.txt must match platform, recipe and
package and its checksum; a missing file stops configure with a capture hint.
Capture mode is opt-in, queries the target and stores normalized answers.
Waf's own samba_cross.py (from the extracted talloc or tdb source) reads the
replayed file, so the format is checked against the real reader.

Usage: waf-answers.py --bmake BMAKE --pkgsrc TREE --makeconf CROSS_MAKECONF
                      --samba-cross WRKSRC/buildtools/wafsamba/samba_cross.py
"""
import argparse
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest

ARGS = None
RECIPES = ('devel/talloc', 'databases/tdb')
TOOL = 'devel/talloc/files/waf_answers.py'
ANSWERS = ('Checking simple C program: "NetBSD"\n'
           'rpath library support: OK\n'
           'Checking for HAVE_SECURE_MKSTEMP: OK\n'
           'Checking for working strptime: NO\n'
           'Checking value of NSIG: "33"\n'
           'Checking errno of iconv for illegal multibyte sequence: (1, "86")\n')


def tool(*args):
    return subprocess.run([sys.executable, '-B', '-E', '-S', str(ARGS.pkgsrc / TOOL), *map(str, args)],
                          capture_output=True, text=True, timeout=60)


def bmake(recipe, *args):
    return subprocess.run([ARGS.bmake, '-C', str(ARGS.pkgsrc / recipe), f'MAKECONF={ARGS.makeconf}', *args],
                          capture_output=True, text=True, timeout=300, env=dict(os.environ, LC_ALL='C'))


def value(recipe, expression, *args):
    result = bmake(recipe, *args, '-V', expression)
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    return result.stdout.strip()


def samba_cross():
    """Waf's samba_cross module with stub waflib imports."""
    class WafError(Exception):
        pass
    waflib = types.ModuleType('waflib')
    stubs = {'Utils': types.SimpleNamespace(subprocess=subprocess), 'Logs': types.SimpleNamespace(),
             'Options': types.SimpleNamespace(), 'Errors': types.SimpleNamespace(WafError=WafError),
             'Context': types.SimpleNamespace()}
    for name, stub in stubs.items():
        setattr(waflib, name, stub)
    configure = types.ModuleType('waflib.Configure')
    configure.conf = lambda function: function
    wafsamba = types.ModuleType('wafsamba')
    wafsamba.samba_utils = types.ModuleType('wafsamba.samba_utils')
    saved = {name: sys.modules.get(name) for name in ('waflib', 'waflib.Configure', 'wafsamba', 'wafsamba.samba_utils')}
    sys.modules.update({'waflib': waflib, 'waflib.Configure': configure, 'wafsamba': wafsamba,
                        'wafsamba.samba_utils': wafsamba.samba_utils})
    try:
        spec = importlib.util.spec_from_file_location('ember_samba_cross', ARGS.samba_cross)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        for name, module_saved in saved.items():
            if module_saved is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module_saved
    return module


class Helper(unittest.TestCase):
    ident = ('NetBSD-11.0-aarch64', 'databases/tdb', 'tdb-1.4.15')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def capture(self, text, *forbidden):
        answers = self.root / 'work.txt'
        answers.write_text(text)
        (self.root / 'capture').mkdir(exist_ok=True)
        return tool('store', *self.ident, answers, self.root / 'capture', *forbidden)

    def stored(self):
        return self.root / 'capture' / 'NetBSD-11.0-aarch64' / 'databases_tdb.txt'

    def test_store_normalizes_and_replay_round_trips(self):
        raw = '# comment\n\n  ' + ANSWERS.replace('\n', '  \n') + 'rpath library support: OK\n'
        result = self.capture(raw)
        self.assertEqual(result.returncode, 0, result.stderr)
        text = self.stored().read_text()
        self.assertTrue(text.startswith('# EmberBSD Waf cross answers 1\n# platform: NetBSD-11.0-aarch64\n'
                                        '# recipe: databases/tdb\n# package: tdb-1.4.15\n# answers-sha256: '))
        self.assertTrue(text.endswith(ANSWERS), text)
        output = self.root / 'replayed.txt'
        result = tool('replay', *self.ident, self.stored(), output)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output.read_text(), text)
        # Waf's own reader answers every probe from the replayed file.
        waf = samba_cross()
        expected = {'Checking simple C program': (0, 'NetBSD'), 'rpath library support': waf.ANSWER_OK,
                    'Checking for working strptime': waf.ANSWER_NO, 'Checking value of NSIG': (0, '33'),
                    'Checking errno of iconv for illegal multibyte sequence': (1, '86')}
        for message, answer in expected.items():
            self.assertEqual(waf.cross_answer(str(output), message), answer, message)
        self.assertEqual(waf.cross_answer(str(output), 'An unasked probe'), waf.ANSWER_UNKNOWN)

    def test_store_accepts_what_waf_writes(self):
        waf = samba_cross()
        written = self.root / 'waf.txt'
        for message, answer in (('a', (0, '')), ('b', (1, '')), ('c', (0, 'x y')), ('d', (2, 'z')), ('e', (3, ''))):
            waf.add_answer(str(written), message, answer)
        result = self.capture(written.read_text())
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_store_refuses_incomplete_or_bad_answers(self):
        for text, message in ((ANSWERS + 'Checking for X: UNKNOWN\n', 'unanswered probe'),
                              ('Checking for X: maybe\n', 'bad answer format'),
                              ('Checking for X: OK\nChecking for X: NO\n', 'conflicting answers'),
                              ('# nothing\n', 'no answers')):
            with self.subTest(message=message):
                result = self.capture(text)
                self.assertEqual(result.returncode, 1)
                self.assertIn(message, result.stderr)
                self.assertFalse(self.stored().exists())

    def test_store_refuses_build_paths_and_existing_files(self):
        result = self.capture('Checking path: "/build/work/x"\n', '/build/work')
        self.assertEqual(result.returncode, 1)
        self.assertIn('build path', result.stderr)
        self.assertEqual(self.capture(ANSWERS).returncode, 0)
        again = self.capture(ANSWERS)
        self.assertEqual(again.returncode, 1)
        self.assertIn('exists', again.stderr)

    def test_replay_refuses_other_builds_and_changed_answers(self):
        self.assertEqual(self.capture(ANSWERS).returncode, 0)
        for index, other in ((0, 'NetBSD-11.0-x86_64'), (1, 'devel/talloc'), (2, 'tdb-1.4.16')):
            with self.subTest(other=other):
                ident = list(self.ident)
                ident[index] = other
                result = tool('replay', *ident, self.stored(), self.root / f'out{index}.txt')
                self.assertEqual(result.returncode, 1)
                self.assertIn('stored answers are for', result.stderr)
        self.stored().write_text(self.stored().read_text().replace('"33"', '"65"'))
        changed = tool('replay', *self.ident, self.stored(), self.root / 'changed.txt')
        self.assertEqual(changed.returncode, 1)
        self.assertIn('checksum', changed.stderr)
        missing = tool('replay', *self.ident, self.root / 'missing.txt', self.root / 'missing-out.txt')
        self.assertEqual(missing.returncode, 1)
        self.assertIn('No stored Waf cross answers for NetBSD-11.0-aarch64 in databases/tdb', missing.stderr)


class Recipes(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def identity(self, recipe):
        return (value(recipe, '${CROSS_OPSYS}-${CROSS_OS_VERSION}-${MACHINE_ARCH}'), recipe,
                value(recipe, '${PKGNAME_NOREV}'))

    def test_default_replays_without_a_target(self):
        for recipe in RECIPES:
            with self.subTest(recipe=recipe):
                platform = self.identity(recipe)[0]
                self.assertEqual(value(recipe, '${USE_CROSS_COMPILE}'), 'yes')
                self.assertEqual(value(recipe, '${EMBERBSD_WAF_ANSWERS_MODE}'), 'replay')
                self.assertEqual(value(recipe, '${EMBERBSD_WAF_ANSWERS}'),
                                 str(ARGS.pkgsrc / recipe / 'files' / 'cross-answers' / f'{platform}.txt'))
                self.assertEqual(value(recipe, '${PKG_FAIL_REASON}'), '')
                arguments = value(recipe, '${CONFIGURE_ARGS}').split()
                work = value(recipe, '${WRKDIR}')
                self.assertIn('--cross-compile', arguments)
                self.assertIn(f'--cross-answers={work}/.cross-answers.txt', arguments)
                self.assertFalse([a for a in arguments if a.startswith('--cross-execute')], arguments)
                printed = bmake(recipe, '-n', 'pre-configure')
                self.assertEqual(printed.returncode, 0, printed.stderr)
                for live in ('target-query.py', 'EMBERBSD_GI_QUERY_CONFIG'):
                    self.assertNotIn(live, printed.stdout)

    def test_replay_target_installs_matching_stored_answers(self):
        for recipe in RECIPES:
            with self.subTest(recipe=recipe):
                ident = self.identity(recipe)
                capture = self.root / recipe.replace('/', '_')
                capture.mkdir()
                answers = capture / 'answers.txt'
                answers.write_text(ANSWERS)
                self.assertEqual(tool('store', *ident, answers, capture).returncode, 0)
                stored = capture / ident[0] / (recipe.replace('/', '_') + '.txt')
                work = capture / 'work'
                work.mkdir()
                result = bmake(recipe, f'WRKDIR={work}', f'EMBERBSD_WAF_ANSWERS={stored}', 'emberbsd-waf-answers')
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual((work / '.cross-answers.txt').read_text(), stored.read_text())
                missing = bmake(recipe, f'WRKDIR={work}', f'EMBERBSD_WAF_ANSWERS={capture}/none.txt',
                                'emberbsd-waf-answers')
                self.assertNotEqual(missing.returncode, 0)
                self.assertIn(f'No stored Waf cross answers for {ident[0]} in {recipe}', missing.stdout + missing.stderr)
                other = 'databases/tdb' if recipe == 'devel/talloc' else 'devel/talloc'
                foreign = bmake(other, f'WRKDIR={work}', f'EMBERBSD_WAF_ANSWERS={stored}', 'emberbsd-waf-answers')
                self.assertNotEqual(foreign.returncode, 0)
                self.assertIn('stored answers are for recipe', foreign.stdout + foreign.stderr)

    def test_capture_is_opt_in_and_gated(self):
        query = self.root / 'query.json'
        query.write_text('{}\n')
        for recipe in RECIPES:
            with self.subTest(recipe=recipe):
                ident = self.identity(recipe)
                capture = self.root / ('capture-' + recipe.replace('/', '_'))
                capture.mkdir()
                mode = ('EMBERBSD_WAF_ANSWERS_MODE=capture', f'EMBERBSD_WAF_ANSWERS_CAPTURE_DIR={capture}')
                arguments = value(recipe, '${CONFIGURE_ARGS}', *mode)
                self.assertIn('--cross-execute=', arguments)
                self.assertIn('--jobs=1', arguments)
                refused = bmake(recipe, *mode, 'emberbsd-waf-inputs')
                self.assertNotEqual(refused.returncode, 0)
                self.assertIn('EMBERBSD_GI_QUERY_CONFIG must name', refused.stdout + refused.stderr)
                accepted = bmake(recipe, *mode, f'EMBERBSD_GI_QUERY_CONFIG={query}', 'emberbsd-waf-inputs')
                self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)
                nodir = bmake(recipe, 'EMBERBSD_WAF_ANSWERS_MODE=capture', f'EMBERBSD_GI_QUERY_CONFIG={query}',
                              'emberbsd-waf-inputs')
                self.assertNotEqual(nodir.returncode, 0)
                self.assertIn('EMBERBSD_WAF_ANSWERS_CAPTURE_DIR must name', nodir.stdout + nodir.stderr)
                work = capture / 'work'
                work.mkdir()
                (work / '.cross-answers.txt').write_text(ANSWERS)
                (work / '.waf-query-failure').write_text('Injected transport failure\n')
                failed = bmake(recipe, *mode, f'WRKDIR={work}', 'emberbsd-waf-capture')
                self.assertNotEqual(failed.returncode, 0)
                self.assertIn('Injected transport failure', failed.stdout + failed.stderr)
                (work / '.waf-query-failure').unlink()
                stored = bmake(recipe, *mode, f'WRKDIR={work}', 'emberbsd-waf-capture')
                self.assertEqual(stored.returncode, 0, stored.stdout + stored.stderr)
                self.assertTrue((capture / ident[0] / (recipe.replace('/', '_') + '.txt')).is_file())

    def test_invalid_mode_and_native_builds(self):
        for recipe in RECIPES:
            with self.subTest(recipe=recipe):
                invalid = bmake(recipe, 'EMBERBSD_WAF_ANSWERS_MODE=live', 'emberbsd-waf-answers')
                self.assertNotEqual(invalid.returncode, 0)
                self.assertIn('EMBERBSD_WAF_ANSWERS_MODE must be replay or capture', invalid.stdout + invalid.stderr)
                native = value(recipe, '${CONFIGURE_ARGS}', 'USE_CROSS_COMPILE=no')
                self.assertNotIn('--cross-', native)


def main():
    global ARGS
    parser = argparse.ArgumentParser()
    parser.add_argument('--bmake', required=True)
    parser.add_argument('--pkgsrc', type=Path, required=True)
    parser.add_argument('--makeconf', type=Path, required=True)
    parser.add_argument('--samba-cross', type=Path, required=True)
    ARGS, rest = parser.parse_known_args()
    ARGS.pkgsrc = ARGS.pkgsrc.resolve()
    unittest.main(argv=[sys.argv[0], *rest])


if __name__ == '__main__':
    main()

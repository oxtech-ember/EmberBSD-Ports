#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD; AI-assisted comparison-route regression.
"""Check source and optional real shell flow. Synthetic text is not Mach-O."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
PROFILE = ROOT / 'profiles/development-toolchain'
SOURCE = None
TEST_SHELL = None
TEST_WORK = None


def apply_source(original, patch):
    """Apply the three finite source files at exact hunk positions."""
    lines, result, i = patch.splitlines(keepends=True), {}, 0
    while i < len(lines):
        if not lines[i].startswith('--- '):
            i += 1
            continue
        name = lines[i][4:].strip().removesuffix('.orig')
        assert name in original and lines[i + 1] == '+++ ' + name + '\n'
        before, output, cursor = original[name].splitlines(keepends=True), [], 0
        i += 2
        while i < len(lines) and lines[i].startswith('@@ '):
            match = re.fullmatch(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@\n', lines[i])
            assert match
            start, old_count, new_count = int(match[1]) - 1, int(match[2] or 1), int(match[4] or 1)
            assert start >= cursor
            output.extend(before[cursor:start])
            old, new = [], []
            i += 1
            while i < len(lines) and lines[i][:1] in (' ', '+', '-'):
                line = lines[i]
                if line.startswith('--- '):
                    break
                if line[0] in ' -':
                    old.append(line[1:])
                if line[0] in ' +':
                    new.append(line[1:])
                i += 1
            assert len(old) == old_count and len(new) == new_count
            assert before[start:start + old_count] == old
            output.extend(new)
            cursor = start + old_count
        output.extend(before[cursor:])
        result[name] = ''.join(output)
    assert set(result) == set(original)
    return result


TOOLS = r'''import json, os, pathlib, re, sys
name, args = pathlib.Path(sys.argv[0]).name, sys.argv[1:]
with open(os.environ['CALLS'], 'a') as stream:
    stream.write(json.dumps([name, args]) + '\n')
if name == 'uname':
    print('Darwin')
elif name in ('selected-strip', 'ld'):
    if name == 'selected-strip':
        if args == ['--help']: sys.exit(1)
        assert args[:2] == ['-S', '-o'] and len(args) == 4
        if os.environ.get('STRIP_FAILURE') == '1': sys.exit(17)
        target, source = args[2], args[3]
    else:
        assert args[:3] == ['-S', '-r', '-no_uuid'] and args[4] == '-o'
        if os.environ.get('LD_FAILURE') == '1': sys.exit(19)
        source, target = args[3], args[5]
    data = pathlib.Path(source).read_bytes()
    pathlib.Path(target).write_bytes(b''.join(row for row in data.splitlines(keepends=True)
                                             if not row.startswith(b'DWARF:')))
elif name == 'cmp':
    try:
        status = 0 if pathlib.Path(args[0]).read_bytes() == pathlib.Path(args[1]).read_bytes() else 1
    except OSError as error:
        print('cmp: ' + str(error), file=sys.stderr)
        status = 2
    with open(os.environ['CALLS'] + '.cmp-status', 'a') as stream:
        stream.write(json.dumps([args, status]) + '\n')
    sys.exit(status)
elif name == 'rm':
    for arg in args:
        if arg != '-f': pathlib.Path(arg).unlink(missing_ok=True)
elif name in ('cp', 'mv'):
    assert len(args) == 2
    if name == 'cp': pathlib.Path(args[1]).write_bytes(pathlib.Path(args[0]).read_bytes())
    else: pathlib.Path(args[0]).replace(args[1])
elif name == 'awk':
    assert args == ['{ print $2 }']
    for line in sys.stdin:
        words = line.split()
        if len(words) >= 2: print(words[1])
elif name == 'sort':
    assert args == ['-u']
    sys.stdout.write(''.join(sorted(set(sys.stdin.readlines()))))
elif name == 'sed':
    if args == [r'$s,\.[^.]*$,,']:
        print(sys.stdin.read().rstrip('\n').rsplit('.', 1)[0])
    else:
        assert len(args) == 2 and args[0] == '-n'
        assert args[1].replace('\t', r'\t') == r's,.* \(\.gnu\.lto_[^ \t]*\).*,\1,p'
        for line in sys.stdin:
            match = re.search(r'\.gnu\.lto_[^ \t\n]*', line)
            if match: print(match[0])
elif name in ('objdump', 'selected-objdump'):
    if args == ['--help']:
        print(' --section-headers')
    else:
        assert len(args) == 2 and args[0] == '--section-headers'
        data = pathlib.Path(args[1]).read_bytes()
        print('0 .text')
        for marker, section in ((b'COMMENT:', '.comment'), (b'EH_FRAME:', '.eh_frame'),
                                (b'LTO:', '.gnu.lto_fixture')):
            if marker in data: print('1 ' + section)
elif name == 'grep':
    assert len(args) == 1
    data = sys.stdin.read()
    if 'section-' in args[0]: matched = '--section-headers' in data
    else: matched = re.search(args[0], data) is not None
    sys.exit(0 if matched else 1)
elif name == 'selected-objcopy':
    if args == ['--help']:
        print(' --remove-section <section>')
    elif args == ['-v']:
        print('no input file specified', file=sys.stderr)
        sys.exit(1)
    else:
        markers = {'.comment': b'COMMENT:', '.eh_frame': b'EH_FRAME:',
                   '.rel.eh_frame': b'REL_EH:', '.rela.eh_frame': b'RELA_EH:',
                   '.gnu.lto_fixture': b'LTO:'}
        remove = []
        while args[:1] == ['--remove-section']:
            assert len(args) >= 3 and args[1] in markers
            remove.append(markers[args[1]])
            args = args[2:]
        assert remove and len(args) in (1, 2)
        if os.environ.get('OBJCOPY_FAILURE') == 'True':
            print('selected objcopy operation failed', file=sys.stderr)
            sys.exit(23)
        data = pathlib.Path(args[0]).read_bytes()
        pathlib.Path(args[-1]).write_bytes(b''.join(row for row in data.splitlines(keepends=True)
                                                 if not row.startswith(tuple(remove))))
        if os.environ.get('OBJCOPY_FAILURE') == 'after-write':
            print('selected objcopy wrote output then failed', file=sys.stderr)
            sys.exit(23)
elif name in ('objcopy', 'readelf', 'eu-readelf', 'strip'):
    sys.exit(1)
else:
    raise AssertionError((name, args))
'''


class CompareSourceTests(unittest.TestCase):
    def source(self):
        if SOURCE is None:
            self.skipTest('Pass --gcc-source for exact GCC source-hunk checks')
        original = {name: (SOURCE / name).read_text()
                    for name in ('contrib/compare-debug', 'configure.ac', 'configure')}
        patch = (PROFILE / 'patches/gcc-darwin-compare-debug.patch').read_text()
        return original, apply_source(original, patch)

    def test_recipe_binds_both_routes_and_preserves_checks(self):
        path = PROFILE / 'tests/darwin-native-provider.py'
        spec = importlib.util.spec_from_file_location('provider_source_control', path)
        module = importlib.util.module_from_spec(spec)
        exec(compile(path.read_bytes(), str(path), 'exec'), module.__dict__)
        text = (PROFILE / 'patches/gcc-darwin-host.patch').read_text()
        module.check_recipe(text)
        bindings = ['+' + env + '+= GCC_COMPARE_DEBUG_STRIP=${STRIP:Q}\n'
                    for env in ('CONFIGURE_ENV', 'MAKE_ENV')]
        bindings += ['+' + env + '+= GCC_COMPARE_DEBUG_' + name +
                     '=${LOCALBASE:Q}/bin/llvm-' + tool + '\n'
                     for env in ('CONFIGURE_ENV', 'MAKE_ENV')
                     for name, tool in (('OBJDUMP', 'objdump'), ('OBJCOPY', 'objcopy'))]
        for line in bindings:
            with self.assertRaises(AssertionError):
                module.check_recipe(text.replace(line, ''))
        with self.assertRaises(AssertionError):
            module.check_recipe(text + '+CONFIGURE_ARGS+= --enable-stage1-checking=release\n')

    def test_export_registers_one_recipe_patch(self):
        row = ('recipe-patch\tprofiles/development-toolchain/patches/gcc-darwin-compare-debug.patch'
               '\tlang/gcc16\tpatch-contrib_compare_debug_selected_strip\n')
        self.assertEqual((ROOT / 'pkgsrc/export.conf').read_text().count(row), 1)

    def test_exact_configure_and_comparison_source(self):
        original, fixed = self.source()
        for name in ('configure.ac', 'configure'):
            selected = ('       (if test "${GCC_COMPARE_DEBUG_STRIP+set}" = set; then\n'
                '          "$SHELL" "${srcdir}/contrib/compare-debug" conftest.o.g0 conftest.o.g\n'
                '        else\n'
                '          ${srcdir}/contrib/compare-debug conftest.o.g0 conftest.o.g\n'
                '        fi) > /dev/null 2>&1; then\n')
            before = '       ${srcdir}/contrib/compare-debug conftest.o.g0 conftest.o.g > /dev/null 2>&1; then\n'
            message = 'selected Darwin bootstrap-debug comparison failed'
            fail = ('AC_MSG_ERROR([' + message + '])' if name == 'configure.ac' else
                    'as_fn_error $? "' + message + '" "$LINENO" 5')
            guard = ('      if test "${GCC_COMPARE_DEBUG_STRIP+set}" = set; then\n'
                     '        case $build in\n        *-*-darwin*) ' + fail + ' ;;\n'
                     '        esac\n      fi\n')
            self.assertEqual(fixed[name].replace(selected, before).replace(guard, ''), original[name])
            self.assertIn(guard, fixed[name])
            self.assertIn('${CC} -c -g conftest.c', fixed[name])
            self.assertIn('BUILD_CONFIG=\n', fixed[name])
        script = fixed['contrib/compare-debug']
        self.assertEqual(script.count('"$strip_tool" -S -o'), 2)
        self.assertIn('test -x "$normalizer"', script)
        self.assertIn('objdump_tool=$GCC_COMPARE_DEBUG_OBJDUMP', script)
        self.assertIn('objcopy_tool=$GCC_COMPARE_DEBUG_OBJCOPY', script)
        self.assertIn('objcopy_probe=-v\n', script)
        self.assertIn('    objcopy_probe=--help\n', script)
        self.assertEqual(script.count('("$objcopy_tool" "$objcopy_probe")'), 2)
        self.assertEqual(script.count('|| exit 1'), 5)
        self.assertEqual(script.count('test "$selected_darwin_tools" != yes || exit 1'), 3)
        self.assertIn('ld -S -r -no_uuid "$1"', script)
        tail = original['contrib/compare-debug'][original['contrib/compare-debug'].index('remove_comment ()'):]
        allowed = {
            'for s in `objdump --section-headers "$file"': 'for s in `"$objdump_tool" --section-headers "$file"',
            '[ -n "$opts" ] && objcopy $opts $file': ('[ -n "$opts" ] && {\n'
                '    "$objcopy_tool" $opts "$file" || {\n'
                '      test "$selected_darwin_tools" != yes || exit 1\n    }\n  }'),
            '(objcopy -v)': '("$objcopy_tool" "$objcopy_probe")',
            '(objdump --help)': '("$objdump_tool" --help)',
            'if ($t --help)': 'if ("$t" --help)',
            'for t in objdump readelf eu-readelf; do': 'for t in "$objdump_tool" readelf eu-readelf; do\n    if test "$selected_darwin_tools" = yes && test "$t" != "$objdump_tool"; then\n      break\n    fi',
            '$cmd --section-headers': '"$cmd" --section-headers',
            '      objcopy $rsopts "$1.$suf1" "$1.$suf3"': '      "$objcopy_tool" $rsopts "$1.$suf1" "$1.$suf3" || {\n        test "$selected_darwin_tools" != yes || exit 1\n      }',
            '      objcopy $rsopts "$2.$suf2" "$2.$suf4"': '      "$objcopy_tool" $rsopts "$2.$suf2" "$2.$suf4" || {\n        test "$selected_darwin_tools" != yes || exit 1\n      }',
            '(strip --help)': '("$strip_tool" --help)',
            '      strip $rsopts': '      "$strip_tool" $rsopts',
            'trap "exit $status; exit" 0 1 2 15': "trap 'exit $status; exit' 0 1 2 15",
            '    status=$?\n': '    status=1\n',
        }
        for before, after in allowed.items():
            tail = tail.replace(before, after)
        self.assertEqual(script[script.index('remove_comment ()'):], tail)

    def test_changed_source_context_refuses(self):
        original, _ = self.source()
        original['contrib/compare-debug'] = original['contrib/compare-debug'].replace(
            '  ld -S -r -no_uuid "$1"', '  changed-ld -S -r -no_uuid "$1"')
        with self.assertRaises(AssertionError):
            apply_source(original, (PROFILE / 'patches/gcc-darwin-compare-debug.patch').read_text())

    def shell_case(self, name, *, different=False, failure=False, selection='selected',
                   old=False, bad_normalizer=None, gkd=None, section=None,
                   legacy_probe=False, objcopy_failure=False, guardless=False):
        if TEST_SHELL is None:
            self.skipTest('Pass --test-shell and --test-work for real shell flow with Python control tools')
        original, fixed = self.source()
        work = TEST_WORK / name
        work.mkdir()
        tools = work / 'bin'
        tools.mkdir()
        for tool in ('uname', 'selected-strip', 'ld', 'cmp', 'rm', 'sed', 'awk', 'sort', 'cp', 'mv', 'objdump',
                     'objcopy', 'selected-objdump', 'selected-objcopy', 'grep', 'readelf', 'eu-readelf', 'strip'):
            path = tools / tool
            path.write_text('#!' + sys.executable + '\n' + TOOLS)
            path.chmod(0o755)
        script = work / 'compare-debug'
        body = (original if old else fixed)['contrib/compare-debug']
        if legacy_probe:
            assert body.count('    objcopy_probe=--help\n') == 1
            body = body.replace('    objcopy_probe=--help\n', '    objcopy_probe=-v\n')
        if guardless:
            pattern = r' \|\| \{\n *test "\$selected_darwin_tools" != yes \|\| exit 1\n *\}'
            body, count = re.subn(pattern, '', body)
            assert count == 3
        script.write_text(body)
        left, right = work / 'left.o', work / 'right.o'
        left.write_text('TEXT:left\nDWARF:one\n')
        right.write_text(('TEXT:changed\n' if different else 'TEXT:left\n') + 'DWARF:two\n')
        if section is not None:
            assert section in ('comment', 'cfi', 'lto')
            left.write_text(left.read_text() + {'comment': 'COMMENT:left\n',
                'cfi': 'EH_FRAME:left\n', 'lto': 'LTO:left\n'}[section])
            if section != 'cfi':
                right.write_text(right.read_text() + {'comment': 'COMMENT:right\n',
                    'lto': 'LTO:right\n'}[section])
        if gkd is not None:
            (work / 'left.1.gkd').write_text('tree:one\n')
            if gkd != 'one-sided':
                (work / 'right.1.gkd').write_text('tree:two\n')
        calls = work / 'calls.jsonl'
        env = dict(PATH=str(tools), LC_ALL='C', CALLS=str(calls))
        if selection != 'unset':
            env['GCC_COMPARE_DEBUG_STRIP'] = str(tools / 'selected-strip') if selection == 'selected' else selection
            env['GCC_COMPARE_DEBUG_OBJDUMP'] = str(tools / 'selected-objdump')
            env['GCC_COMPARE_DEBUG_OBJCOPY'] = str(tools / 'selected-objcopy')
            if gkd is None:
                env['LD_FAILURE'] = '1'
            if bad_normalizer is not None:
                key, value = bad_normalizer
                if value is None:
                    del env[key]
                else:
                    env[key] = value
        if failure:
            env['STRIP_FAILURE'] = '1'
        if objcopy_failure:
            env['OBJCOPY_FAILURE'] = str(objcopy_failure)
        completed = subprocess.run([str(TEST_SHELL), str(script), str(left), str(right)],
                                   cwd=work, env=env, capture_output=True, timeout=30)
        (work / 'stdout').write_bytes(completed.stdout)
        (work / 'stderr').write_bytes(completed.stderr)
        records = [json.loads(line) for line in calls.read_text().splitlines()]
        (work / 'result.json').write_text(json.dumps(dict(exit=completed.returncode,
            shell=str(TEST_SHELL), shell_sha256=hashlib.sha256(TEST_SHELL.read_bytes()).hexdigest(),
            python=sys.executable, calls=records, native_object_or_provider_qualification=False), indent=2) + '\n')
        return completed, records

    def test_shell_debug_only_difference(self):
        result, calls = self.shell_case('debug-only')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(sum(name == 'selected-strip' for name, _ in calls), 2)
        self.assertFalse(any(name == 'ld' for name, _ in calls))

    def test_shell_code_difference_survives_fallback(self):
        result, calls = self.shell_case('changed-code', different=True)
        self.assertEqual(result.returncode, 1)
        self.assertTrue(any(name == 'selected-objcopy' for name, _ in calls))
        self.assertTrue(any(name == 'selected-objdump' for name, _ in calls))
        self.assertFalse(any(name in ('objdump', 'objcopy', 'readelf', 'eu-readelf', 'strip') for name, _ in calls))

    def test_shell_selected_objcopy_help_reaches_comment_removal(self):
        for legacy in (True, False):
            result, calls = self.shell_case('comment-probe-' + str(legacy),
                section='comment', legacy_probe=legacy)
            self.assertEqual(result.returncode, 1 if legacy else 0)
            operations = [args for name, args in calls
                          if name == 'selected-objcopy' and args[:1] == ['--remove-section']]
            self.assertEqual(len(operations), 0 if legacy else 2)
            if not legacy:
                self.assertTrue(any(name == 'awk' for name, _ in calls))
                self.assertFalse(any(name == 'selected-objcopy' and args == ['-v'] for name, args in calls))

    def test_shell_selected_objcopy_help_reaches_cfi_and_lto_removal(self):
        for section in ('cfi', 'lto'):
            for legacy in (True, False):
                result, calls = self.shell_case(section + '-probe-' + str(legacy),
                    section=section, legacy_probe=legacy)
                self.assertEqual(result.returncode, 1 if legacy else 0)
                operations = [args for name, args in calls
                              if name == 'selected-objcopy' and args[:1] == ['--remove-section']]
                self.assertEqual(len(operations), 0 if legacy else 2)
                if not legacy:
                    self.assertTrue(any(name == 'mv' for name, _ in calls))

    def test_shell_selected_objcopy_operation_failure_cannot_pass(self):
        for section in ('comment', 'cfi', 'lto'):
            result, calls = self.shell_case(section + '-objcopy-failure',
                section=section, objcopy_failure=True)
            self.assertEqual(result.returncode, 1)
            self.assertTrue(any(name == 'selected-objcopy' and args[:1] == ['--remove-section']
                                for name, args in calls))

    def test_shell_selected_objcopy_write_then_error_cannot_pass(self):
        for section in ('comment', 'cfi', 'lto'):
            for guardless in (True, False):
                result, calls = self.shell_case(section + '-write-then-error-' + str(guardless),
                    section=section, objcopy_failure='after-write', guardless=guardless)
                self.assertEqual(result.returncode, 0 if guardless else 1)
                self.assertTrue(any(name == 'selected-objcopy' and args[:1] == ['--remove-section']
                                    for name, args in calls))

    def test_shell_strip_failure_cannot_pass(self):
        result, calls = self.shell_case('strip-failure', failure=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(sum(name == 'selected-strip' for name, _ in calls), 1)

    def test_shell_bad_selection_cannot_use_default_linker(self):
        for value, name in (('', 'empty-selection'), ('relative-strip', 'relative-selection'),
                            (str(TEST_WORK / 'absent-strip') if TEST_WORK else '/absent-strip', 'absent-selection')):
            result, calls = self.shell_case(name, selection=value)
            self.assertEqual(result.returncode, 1)
            self.assertFalse(any(tool in ('ld', 'selected-strip') for tool, _ in calls))

    def test_shell_bad_normalizer_cannot_search_path(self):
        for key in ('GCC_COMPARE_DEBUG_OBJDUMP', 'GCC_COMPARE_DEBUG_OBJCOPY'):
            for value, suffix in ((None, 'missing'), ('relative-tool', 'relative'),
                                   (str(TEST_WORK / 'absent-normalizer') if TEST_WORK else '/absent-normalizer', 'absent'),
                                   (str(TEST_WORK) if TEST_WORK else '/directory', 'directory')):
                result, calls = self.shell_case(key.lower() + '-' + suffix,
                                                bad_normalizer=(key, value))
                self.assertEqual(result.returncode, 1)
                self.assertFalse(any(name in ('selected-strip', 'objdump', 'objcopy', 'strip') for name, _ in calls))

    def test_shell_late_dump_difference_old_false_equality(self):
        for old in (True, False):
            result, _ = self.shell_case('dump-difference-' + str(old), old=old, gkd='different')
            self.assertEqual(result.returncode, 0 if old else 1)

    def test_shell_one_sided_dump_error_old_false_equality(self):
        for old in (True, False):
            result, _ = self.shell_case('dump-read-error-' + str(old), old=old, gkd='one-sided')
            self.assertEqual(result.returncode, 0 if old else 1)
            statuses = [json.loads(row) for row in (TEST_WORK / ('dump-read-error-' + str(old)) / 'calls.jsonl.cmp-status').read_text().splitlines()]
            self.assertEqual(statuses[-1][1], 2)

    def test_shell_old_linker_route_fails_same_selected_fixture(self):
        result, calls = self.shell_case('old-linker-route', old=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(sum(name == 'ld' for name, _ in calls), 2)
        self.assertFalse(any(name == 'selected-strip' for name, _ in calls))

    def test_shell_unset_retains_upstream_linker_route(self):
        result, calls = self.shell_case('unset-route', selection='unset')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(sum(name == 'ld' for name, _ in calls), 2)
        self.assertFalse(any(name == 'selected-strip' for name, _ in calls))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gcc-source', type=Path)
    parser.add_argument('--test-shell', type=Path, help='explicit shell for source-test infrastructure only')
    parser.add_argument('--test-work', type=Path, help='new absolute caller-owned test work')
    args, remaining = parser.parse_known_args()
    SOURCE, TEST_SHELL, TEST_WORK = args.gcc_source, args.test_shell, args.test_work
    if TEST_SHELL is not None:
        if (SOURCE is None or not TEST_SHELL.is_absolute() or not TEST_SHELL.is_file()
                or TEST_WORK is None or not TEST_WORK.is_absolute() or TEST_WORK.exists()):
            parser.error('Use --gcc-source, an absolute --test-shell and new --test-work')
        TEST_WORK.mkdir()
    unittest.main(argv=[__file__, *remaining])

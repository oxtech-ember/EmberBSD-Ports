#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that every build selects the one exported Ruby, from real pkgsrc metadata.

The export keeps only lang/ruby40. Its rubyversion.mk supports, accepts and
defaults to 4.0 alone, so the native and cross common tools profiles, host
recursion and a build without any EmberBSD profile (the Darwin bootstrap)
all pick it, and an old RUBY_VERSION_DEFAULT is rejected. No profile sets
its own Ruby default. Usage:

  ruby-selection.py EXPORTED_PKGSRC NATIVE_MAKECONF CROSS_MAKECONF... NEW_WORK

NATIVE_MAKECONF holds the host prefix inputs; the check includes the exported
common tools profile after it. Each CROSS_MAKECONF (one per prepared target)
includes EMBERBSD-CROSS-MK.CONF once; the check points that include at the
export under test and also queries host recursion for the first one.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
KEYS = ('RUBY_VERSION_DEFAULT', 'RUBY_VER', 'RUBY_VERSION', 'RUBY_PKGPREFIX', 'PKGNAME',
        'USE_CROSS_COMPILE', 'CMAKE_CONFIGURE_ARGS', 'PKG_FAIL_REASON')
SETTING = re.compile(r'^RUBY_VERSION_DEFAULT\s*[?:+!]?=.*\n', re.M)
CROSS_INCLUDE = re.compile(r'^\.include "[^"\n]*(?:/profiles/common-build-tools/cross/mk\.conf|'
                           r'/EMBERBSD-CROSS-MK\.CONF)"$', re.M)


def fail(message):
    print('FAIL: ' + message)
    sys.exit(1)


def main():
    if len(sys.argv) < 5:
        print(__doc__.strip().splitlines()[-7], file=sys.stderr)
        return 2
    tree, native_conf = (Path(p).resolve() for p in sys.argv[1:3])
    cross_confs = [Path(p).resolve() for p in sys.argv[3:-1]]
    work = Path(sys.argv[-1]).absolute()
    if os.path.lexists(work):
        fail('output exists: ' + str(work))
    work.mkdir(parents=True)
    bmake = os.environ.get('BMAKE', 'bmake')

    # One source of the Ruby choice: the exported rubyversion.mk.
    for path in sorted(ROOT.glob('profiles/**/*mk.conf')) + [ROOT / 'pkgsrc/defaults.mk.conf',
                                                             ROOT / 'pkgsrc/versions.mk']:
        if SETTING.search(path.read_text()):
            fail(str(path.relative_to(ROOT)) + ' sets its own RUBY_VERSION_DEFAULT')
    ruby = (tree / 'lang/ruby/rubyversion.mk').read_text()
    supported = re.search(r'^RUBY_VERSIONS_SUPPORTED=\s*(.*)$', ruby, re.M).group(1).split()
    kept = sorted(p.name[4:] for p in (tree / 'lang').glob('ruby[0-9]*'))
    if supported != kept or len(kept) != 1:
        fail('rubyversion.mk supports %s; the export has %s' % (' '.join(supported), ' '.join(kept)))
    version = re.search(r'^RUBY%s_VERSION=\s*(\S+)$' % kept[0], ruby, re.M).group(1)

    host = SETTING.sub('', native_conf.read_text())
    configs = {
        'plain': host,
        'native': host + '\nPREFIX?=${LOCALBASE}\n.include "%s/EMBERBSD-COMMON-TOOLS-MK.CONF"\n' % tree,
    }
    for index, cross_conf in enumerate(cross_confs):
        cross = SETTING.sub('', cross_conf.read_text())
        if len(CROSS_INCLUDE.findall(cross)) != 1:
            fail('expected one cross-profile include in ' + str(cross_conf))
        configs['cross%d' % index] = CROSS_INCLUDE.sub(
            '.include "%s/EMBERBSD-CROSS-MK.CONF"' % tree, cross)
    configs['native-cross'] = configs['cross0'] + \
        '\nPREFIX?=${LOCALBASE}\n.include "%s/EMBERBSD-COMMON-TOOLS-MK.CONF"\n' % tree
    for name, text in configs.items():
        (work / (name + '.conf')).write_text(text)
    commands = []

    def query(name, conf, extra=(), succeed=True):
        argv = [bmake, '-C', str(tree / 'textproc/ruby-asciidoctor'),
                'MAKECONF=' + str(work / (conf + '.conf')), 'WRKOBJDIR=' + str(work / 'objects'),
                'PACKAGES=' + str(work / 'packages'), '_PKGSRC_BARRIER=yes', *extra]
        for key in KEYS:
            argv += ['-V', '${%s}' % key]
        result = subprocess.run(argv, capture_output=True, text=True, env=dict(os.environ, LC_ALL='C'))
        (work / (name + '.stdout')).write_text(result.stdout)
        (work / (name + '.stderr')).write_text(result.stderr)
        commands.append({'name': name, 'argv': argv, 'status': result.returncode})
        (work / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        if not succeed:
            return result
        lines = result.stdout.split('\n')[:-1]
        if result.returncode != 0 or len(lines) != len(KEYS):
            fail('metadata query %s failed: %s' % (name, result.stderr.strip()[-400:]))
        return dict(zip(KEYS, lines))

    results = {}
    queries = [('plain', 'plain', ()), ('native', 'native', ())]
    queries += [('cross%d' % i, 'cross%d' % i, ()) for i in range(len(cross_confs))]
    queries.append(('host-recursion', 'cross0', ('USE_CROSS_COMPILE=no',)))
    for name, conf, extra in queries:
        data = query(name, conf, extra)
        want = {'RUBY_VERSION_DEFAULT': kept[0], 'RUBY_VER': kept[0], 'RUBY_VERSION': version,
                'RUBY_PKGPREFIX': 'ruby' + kept[0]}
        wrong = {k: data[k] for k, v in want.items() if data[k] != v}
        if wrong or not data['PKGNAME'].startswith('ruby%s-asciidoctor-' % kept[0]):
            fail('%s selects %s %s, not Ruby %s' % (name, wrong, data['PKGNAME'], version))
        if 'requires the current Ruby' in data['PKG_FAIL_REASON']:
            fail(name + ' still carries a profile Ruby barrier')
        results[name] = data
    recursion = results['host-recursion']
    if recursion['USE_CROSS_COMPILE'] != 'no' or '-DCMAKE_SYSTEM_NAME' in recursion['CMAKE_CONFIGURE_ARGS']:
        fail('host Ruby recursion was forced cross')
    for conf in ('plain', 'native', 'cross0'):
        old = query('override-' + conf, conf, ('RUBY_VERSION_DEFAULT=34',), succeed=False)
        if old.returncode == 0 or 'Unsupported RUBY_VERSION_DEFAULT: 34' not in old.stderr:
            fail('RUBY_VERSION_DEFAULT=34 was not rejected in ' + conf)
    barrier = query('native-cross-rejected', 'native-cross', succeed=False)
    if barrier.returncode == 0 or 'requires native package builds' not in barrier.stderr:
        fail('the native-only common tools barrier changed')
    (work / 'result.json').write_text(json.dumps({
        'scope': 'pkgsrc metadata for plain, native, cross and host recursion; no Ruby build.',
        'results': results}, indent=2) + '\n')
    print('PASS: %s select Ruby %s; 3.4 is rejected' % (', '.join(results), version))
    return 0


if __name__ == '__main__':
    sys.exit(main())

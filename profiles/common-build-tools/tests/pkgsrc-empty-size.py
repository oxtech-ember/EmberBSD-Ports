#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Run the exported size recipes with selected tools and isolated fixtures."""
import argparse
from pathlib import Path
import os
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--pkgsrc', type=Path, required=True)
p.add_argument('--tools', type=Path, required=True)
p.add_argument('--work', type=Path, required=True)
a = p.parse_args()
a.work = a.work.absolute()
a.work.mkdir(parents=True, exist_ok=False)
tools = {}
for role in ('bmake', 'mksh', 'xargs', 'ls', 'cat', 'sort', 'sed', 'awk', 'mkdir'):
    path = (a.tools / role).absolute()
    if not path.is_file() or not os.access(path, os.X_OK):
        p.error('missing selected executable: ' + str(path))
    tools[role] = str(path)
source = (a.pkgsrc / 'mk/pkgformat/pkg/metadata.mk').read_text()
start = source.index('_SIZE_BATCH=') if '_SIZE_BATCH=' in source else source.index('_SIZE_PKG_FILE=')
end = source.index('### +DEINSTALL/', start)
# Run complete owner recipes. Do not copy their commands into this test.
recipe = source[start:end]
script = a.work / 'pkg-info'
script.write_text('#!' + tools['mksh'] + '\n'
                  'echo "$#" >> "$CALL_LOG"\n'
                  '[ "$1" = -K ] && [ "$2" = fixture-db ] && [ "$3" = -qs ] || exit 91\nshift 3\n'
                  '[ "$#" -gt 0 ] || { echo "missing package name(s)" >&2; exit 92; }\n'
                  'for name do echo 7; done\n')
script.chmod(0o755)
makefile = a.work / 'fixture.mk'
variables = dict(RUN='@', TEST='test', PKG_DB_TMPDIR=str(a.work),
                 PLIST=str(a.work / 'plist'), PREFIX=str(a.work / 'prefix'), DESTDIR='',
                 _RDEPENDS_FILE=str(a.work / 'depends'),
                 _FULL_DEPENDS_CMD=tools['cat'] + ' ' + str(a.work / 'depends'),
                 PKG_INFO=str(script) + ' -K fixture-db', SHELL=tools['mksh'], SH=tools['mksh'])
for role in ('xargs', 'ls', 'cat', 'sort', 'sed', 'awk', 'mkdir'):
    variables[role.upper()] = tools[role]
makefile.write_text('\n'.join(k + '= ' + v for k, v in variables.items()) + '\n' + recipe)
env = dict(HOME=str(a.work), TMPDIR=str(a.work), PATH=str(a.tools.absolute()),
           LC_ALL='C', CALL_LOG=str(a.work / 'calls'))
(a.work / 'prefix').mkdir()
(a.work / 'prefix/file with spaces').write_bytes(b'abcde')
checks = 0
for names, dependencies, expected, batches in (
        ('', '', 0, []),
        ('file with spaces\n', '', 5, []),
        ('file with spaces\n', 'dep-1\n', 12, [4]),
        ('file with spaces\n', 'dep-1\ndep-1\n', 12, [4]),
        ('', ''.join('dep-%03d\n' % i for i in range(300)), 2100, [259, 47])):
    for name in ('+SIZE_PKG', '+SIZE_ALL', 'calls'):
        (a.work / name).unlink(missing_ok=True)
    (a.work / 'plist').write_text(names)
    (a.work / 'depends').write_text(dependencies)
    result = subprocess.run([tools['bmake'], '-r', '-f', str(makefile), str(a.work / '+SIZE_ALL')],
                            cwd=a.work, env=env, capture_output=True)
    assert result.returncode == 0, result.stderr.decode()
    assert not result.stderr, result.stderr.decode()
    assert int((a.work / '+SIZE_ALL').read_text()) == expected
    calls = a.work / 'calls'
    actual = list(map(int, calls.read_text().splitlines())) if calls.exists() else []
    assert actual == batches, (actual, batches)
    checks += 1
print(str(checks) + ' package-size recipe cases passed')

#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Compare the common wrapper's emitted argv with its actual exec argv.

Arguments: selected Python, candidate c++-wrapper, generated c++ config, and
new private work directory. The wrappee is a harmless argv-recording fixture.
"""
import json
import os
from pathlib import Path
import subprocess
import sys

python, wrapper, config, work = map(Path, sys.argv[1:])
assert all(x.is_absolute() for x in (python, wrapper, config, work))
assert python.is_file() and wrapper.is_file() and config.is_file()
assert not os.path.lexists(work)
work.mkdir()
wrappee = work / 'selected-compiler-fixture'
record = work / 'executed.json'
wrappee.write_text('#!' + str(python) + '\nimport json,os,sys\n'
                   'open(os.environ["ARGV_RECORD"],"w").write(json.dumps(sys.argv))\n')
wrappee.chmod(0o755)
lines = [s for s in config.read_text().splitlines()
         if not s.startswith(('worklog=', 'exec=', 'exec_path=', 'path='))]
lines += ['worklog=' + str(work / 'work.log'), 'exec=' + str(wrappee),
          'exec_path=' + str(wrappee), 'path=' + str(python.parent)]
(work / 'c++').write_text('\n'.join(lines) + '\n')
env = dict(os.environ, CWRAPPERS_CONFIG_DIR=str(work), ARGV_RECORD=str(record))
for arguments in (['-c', 'input.cc', '-o', 'output.o', '-DNAME=two words', ''],
                  ['input.o', '-o', 'output', '-Wl,-rpath,/chosen/path']):
    record.unlink(missing_ok=True)
    result = subprocess.run([str(wrapper), *arguments], env=env, capture_output=True, check=True)
    assert not result.stdout
    expected = json.loads(record.read_text())
    record.unlink()
    result = subprocess.run([str(wrapper), *arguments], env={**env, 'CWRAPPERS_EMIT_ARGV': '1'},
                            capture_output=True, check=True)
    assert result.stdout.endswith(b'\0')
    actual = [part.decode() for part in result.stdout[:-1].split(b'\0')]
    assert actual == expected, (actual, expected)
    assert not record.exists(), 'argv emission executed the wrappee'
result = subprocess.run([str(wrapper), '-c', 'input.cc'],
                        env={**env, 'CWRAPPERS_EMIT_ARGV': 'invalid'}, capture_output=True)
assert result.returncode != 0 and not result.stdout
assert not record.exists()
print('PASS: exact transformed argv, compile/link, spaces, empty arg and no exec')

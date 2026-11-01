#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that parallel builds share one build-host llvm-config.

devel/lld and lang/mlir start together after target/native LLVM packages are
installed. Both run lang/llvm/files/cross-llvm-config.py with the same output.
The second must wait for the first and use its result. The installed producer
here is a double that counts concurrent invocations.
Usage: cross-llvm-config-parallel.py [CROSS_LLVM_CONFIG_PY]
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
VERSION = '23.1.4'
DEFAULT = Path(__file__).resolve().parents[3] / 'pkgsrc/lang/llvm/files/cross-llvm-config.py'


def write(path, body, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    path.chmod(mode)


def main():
    script = Path(sys.argv[1] if len(sys.argv) > 1 else DEFAULT).resolve()
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        pkgsrc, state = root / 'pkgsrc', root / 'state'
        producer = pkgsrc / 'lang/llvm/files/build-installed-llvm-config.py'
        config_tool = '#!/bin/sh\necho ' + VERSION + '\n'
        write(producer, f'''import pathlib, sys, time
work = pathlib.Path(sys.argv[2])
if (work / 'helper/bin/llvm-config').is_file():
    sys.exit(0)
work.mkdir()
with open({str(root / 'producer-runs')!r}, 'a') as runs: runs.write('x')
time.sleep(2)
tool = work / 'helper/bin/llvm-config'
tool.parent.mkdir(parents=True)
tool.write_text({config_tool!r}); tool.chmod(0o755)
''')
        (pkgsrc / 'lang/llvm').mkdir(parents=True, exist_ok=True)
        work = state / ('llvm-config-' + VERSION)
        argv = [sys.executable, '-B', str(script), str(work / 'helper/bin/llvm-config'), str(work),
                str(pkgsrc), str(root / 'sysroot')]
        environment = dict(os.environ, EMBERBSD_HOST_PREFIX=str(root / 'host'), EMBERBSD_SDK_SOURCE='')
        jobs = [subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                 env=environment) for _ in range(2)]
        results = [(job.wait(), job.stdout.read()) for job in jobs]
        failed = [output for code, output in results if code != 0]
        if failed:
            print('FAIL: a parallel build did not get the llvm-config: ' + failed[0].strip()[:400])
            return 1
        runs = (root / 'producer-runs').read_text() if (root / 'producer-runs').exists() else ''
        if runs != 'x':
            print('FAIL: the installed producer ran %d times, not once' % len(runs))
            return 1
    print('PASS: parallel builds wait for one build-host llvm-config and use it')
    return 0


if __name__ == '__main__':
    sys.exit(main())

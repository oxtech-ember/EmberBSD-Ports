#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that parallel builds share one build-host llvm-config.

devel/lld and lang/mlir start together once lang/llvm is built. Both run
lang/llvm/files/cross-llvm-config.py with the same CONFIG and NATIVE_WORK.
The second one must wait for the first and use its result, not find the
half-made native tree and fail. The native and config producers here are
doubles that take a while and count their runs.
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
        tools = pkgsrc / 'EMBERBSD-LLVM-CONFIG'
        config_tool = '#!/bin/sh\necho ' + VERSION + '\n'
        write(tools / 'profiles/common-build-tools/cross/build-llvm-native.py', f'''import pathlib, sys, time
native = pathlib.Path(sys.argv[2])
native.mkdir()
with open({str(root / 'native-runs')!r}, 'a') as runs: runs.write('x')
time.sleep(3)
tool = native / 'native/bin/llvm-config'
tool.parent.mkdir(parents=True)
tool.write_text({config_tool!r}); tool.chmod(0o755)
''')
        write(tools / 'scripts/build-llvm-config.py', f'''import pathlib, sys, time
work = pathlib.Path(sys.argv[-1])
work.mkdir()
with open({str(root / 'config-runs')!r}, 'a') as runs: runs.write('x')
time.sleep(1)
tool = work / 'helper/bin/llvm-config'
tool.parent.mkdir(parents=True)
tool.write_text({config_tool!r}); tool.chmod(0o755)
''')
        target = root / 'llvm-build'
        write(target / 'CMakeCache.txt', 'fixture')
        make = root / 'make'
        write(make, '#!/bin/sh\necho ' + str(target) + '\n', 0o755)
        (pkgsrc / 'lang/llvm').mkdir(parents=True)
        work = state / ('llvm-config-' + VERSION)
        argv = [sys.executable, '-B', str(script), str(work / 'helper/bin/llvm-config'), str(work),
                str(state / ('llvm-native-' + VERSION)), str(pkgsrc), str(root / 'sysroot'),
                str(root / 'archive.tar.xz'), str(make)]
        environment = dict(os.environ, EMBERBSD_HOST_PREFIX=str(root / 'host'), EMBERBSD_SDK_SOURCE='')
        jobs = [subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                 env=environment) for _ in range(2)]
        results = [(job.wait(), job.stdout.read()) for job in jobs]
        failed = [output for code, output in results if code != 0]
        if failed:
            print('FAIL: a parallel build did not get the llvm-config: ' + failed[0].strip()[:400])
            return 1
        runs = [(root / name).read_text() if (root / name).exists() else '' for name in ('native-runs', 'config-runs')]
        if runs != ['x', 'x']:
            print('FAIL: the producers ran %d and %d times, not once' % (len(runs[0]), len(runs[1])))
            return 1
    print('PASS: parallel builds wait for one build-host llvm-config and use it')
    return 0


if __name__ == '__main__':
    sys.exit(main())

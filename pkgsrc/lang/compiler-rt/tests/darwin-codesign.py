# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check compiler-rt's real post-build command.
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser()
for name in ('cmake', 'codesign', 'linker', 'launcher', 'lock-root', 'context'):
    parser.add_argument('--' + name, type=Path, required=True)
args = parser.parse_args()
for path in vars(args).values():
    if not path.is_absolute():
        parser.error('all input paths must be absolute')
cc = os.environ['CC']
python = os.environ['PYTHON']
if not Path(cc).is_absolute() or not Path(python).is_absolute():
    parser.error('SDK-selected CC and PYTHON must be absolute')
cmake = args.cmake.read_text()
command = 'COMMAND ${CODESIGN} --force --sign - ${EXTRA_CODESIGN_ARGUMENTS} $<TARGET_FILE:${libname}>'
if cmake.count(command) != 1:
    raise SystemExit('compiler-rt post-build command is not the expected patched command')
with tempfile.TemporaryDirectory(prefix='compiler-rt-codesign-', dir=os.environ['TMPDIR']) as temp:
    root = Path(temp)
    source, dylib = root / 'tiny.c', root / 'tiny.dylib'
    source.write_text('int compiler_rt_codesign_probe(void) { return 1; }\n')
    subprocess.run([python, '-B', str(args.launcher), '--lock-root', str(args.lock_root),
                    '--context', str(args.context), '--', cc, '-dynamiclib',
                    '--ld-path=' + str(args.linker), str(source), '-o', str(dylib)], check=True)
    subprocess.run([str(args.codesign), '--force', '--sign', '-', str(dylib)], check=True)
    original = subprocess.run([str(args.codesign), '--sign', '-', str(dylib)],
                              text=True, capture_output=True)
    if original.returncode == 0 or 'already signed' not in original.stderr.lower():
        raise SystemExit('original command did not refuse the already signed dylib: ' + original.stderr)
    subprocess.run([str(args.codesign), '--force', '--sign', '-', str(dylib)], check=True)
print('PASS: original re-sign refused; patched post-build command re-signs the Mach-O')

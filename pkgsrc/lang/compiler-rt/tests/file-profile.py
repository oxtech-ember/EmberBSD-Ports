# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Exercise the prepared profile implementation against a selected native runtime."""
import argparse
import pathlib
import subprocess
import tempfile

p = argparse.ArgumentParser()
p.add_argument('--cc', type=pathlib.Path, required=True)
p.add_argument('--source', type=pathlib.Path, required=True,
               help='prepared LLVM monorepo source root')
p.add_argument('--profile-file', type=pathlib.Path, help='optional candidate InstrProfilingFile.c')
p.add_argument('--profile-archive', type=pathlib.Path, required=True,
               help='native compiler-rt profile archive for the selected toolchain')
p.add_argument('--cflag', action='append', default=[])
p.add_argument('--ldflag', action='append', default=[])
a = p.parse_args()
source = a.source.resolve(strict=True)
profile = source / 'compiler-rt/lib/profile'
file_c = (a.profile_file or profile / 'InstrProfilingFile.c').resolve(strict=True)
if not file_c.is_file() or not a.profile_archive.is_file():
    p.error('prepared profile source or native profile archive missing')
harness = pathlib.Path(__file__).with_name('file-profile.c')
with tempfile.TemporaryDirectory(prefix='compiler-rt-file-profile-') as tmp:
    binary = pathlib.Path(tmp) / 'file-profile'
    argv = [str(a.cc), *a.cflag, '-ffunction-sections', '-fdata-sections',
            '-I' + str(profile), '-I' + str(source / 'compiler-rt/include'),
            '-DPROFILE_SOURCE="' + str(file_c) + '"', str(harness),
            str(a.profile_archive), *a.ldflag, '-o', str(binary)]
    subprocess.run(argv, check=True)
    subprocess.run([str(binary)], check=True)
print('profile filename ownership and bounds: PASS')

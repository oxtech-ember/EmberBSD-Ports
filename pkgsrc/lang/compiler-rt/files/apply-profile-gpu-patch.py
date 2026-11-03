# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Apply one shared compiler-rt/LLVM patch.
"""Verify the compiler-rt owner's patch and apply it to LLVM's shared header."""
import argparse
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from profile_patch import verified_patch

NAME = 'patch-13-profile-gpu-bounds'
parser = argparse.ArgumentParser(description=__doc__)
for name in ('patch-file', 'distinfo', 'patch-tool', 'workdir'):
    parser.add_argument('--' + name, type=Path, required=True)
args = parser.parse_args()
if any(not value.is_absolute() for value in vars(args).values()):
    parser.error('all selected paths must be absolute')
if args.patch_file.name != NAME:
    parser.error('wrong shared patch name')
try:
    data = verified_patch(args.patch_file, args.distinfo)
    if not args.workdir.is_dir():
        raise ValueError('missing LLVM ProfileData directory')
    subprocess.run([str(args.patch_tool), '-p4', '-f', '-F0', '-d', str(args.workdir)],
                   input=data, check=True)
except (OSError, ValueError, subprocess.CalledProcessError) as exc:
    raise SystemExit('shared GPU profile patch: ' + str(exc)) from exc

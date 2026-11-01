#!/usr/bin/env python3
"""Exercise OpenSSH binary string encoding using an existing native build."""
import argparse
from pathlib import Path
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
for name in ('cc', 'source', 'build-dir', 'prefix', 'work-dir'):
    parser.add_argument('--' + name, type=Path, required=True)
parser.add_argument('--sanitize', action='store_true')
args = parser.parse_args()
args.work_dir.mkdir(parents=True, exist_ok=True)
exe = args.work_dir / 'kerberos-binary-roundtrip'
cmd = [str(args.cc), '-Wall', '-Wextra', '-Werror']
if args.sanitize:
    cmd += ['-fsanitize=address,undefined']
for path in (args.source, args.build_dir, args.prefix / 'include'):
    cmd += ['-I', str(path)]
cmd += [str(Path(__file__).with_suffix('.c')), str(args.build_dir / 'libssh.a'),
        str(args.build_dir / 'openbsd-compat/libopenbsd-compat.a'),
        '-L', str(args.prefix / 'lib'),
        '-Wl,-dead_strip' if sys.platform == 'darwin' else '-Wl,--gc-sections',
        '-lcrypto', '-lz', '-o', str(exe)]
subprocess.run(cmd, check=True)
subprocess.run([str(exe)], check=True)
print('OpenSSH binary string roundtrip: PASS')

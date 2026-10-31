#!/usr/bin/env python3
"""Run ordinary compatibility glob patterns using an existing native build."""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
for name in ('cc', 'source', 'build-dir', 'prefix', 'work-dir'):
    parser.add_argument('--' + name, type=Path, required=True)
parser.add_argument('--sanitize', action='store_true')
args = parser.parse_args()
args.work_dir.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(dir=args.work_dir) as temporary:
    work = Path(temporary)
    for name in ('a.txt', 'b.txt', 'c.log'):
        (work / name).write_text(name + '\n')
    exe = work / 'fixture'
    command = [str(args.cc), '-Wall', '-Wextra', '-Werror', '-DHAVE_CONFIG_H']
    if args.sanitize:
        command += ['-fsanitize=address,undefined']
    for path in (args.build_dir, args.source, args.source / 'openbsd-compat',
                 args.prefix / 'include'):
        command += ['-I', str(path)]
    command += [str(Path(__file__).with_name('fixture.c')),
                str(args.source / 'openbsd-compat/glob.c'),
                str(args.build_dir / 'openbsd-compat/libopenbsd-compat.a'),
                '-Wl,-dead_strip' if sys.platform == 'darwin'
                else '-Wl,--gc-sections', '-o', str(exe)]
    subprocess.run(command, check=True)
    subprocess.run([str(exe)], cwd=work, check=True)
print('OpenSSH compatibility glob ordinary patterns: PASS')

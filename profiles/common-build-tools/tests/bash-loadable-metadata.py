#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Consume actual installed Bash metadata.
import argparse
from pathlib import Path
import shutil
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('stage', 'source', 'make', 'cc', 'readelf', 'work'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--forbid', action='append', required=True)
    args = parser.parse_args()
    if args.stage.parts[-2:] != ('usr', 'pkg'):
        parser.error('--stage must be the canonical staged usr/pkg prefix')
    metadata = args.stage / 'lib/bash/Makefile.inc'
    body = metadata.read_text()
    for path in args.forbid:
        assert path not in body, 'Installed metadata leaks producer path: ' + path
    if not args.work.is_absolute() or args.work.exists():
        parser.error('--work must be a new absolute directory')
    args.work.mkdir()
    shutil.copyfile(args.stage / 'lib/bash/Makefile.sample', args.work / 'Makefile')
    shutil.copyfile(args.source / 'hello.c', args.work / 'example.c')
    shutil.copyfile(args.source / 'loadables.h', args.work / 'loadables.h')
    command = [str(args.make), 'all', 'DESTDIR=' + str(args.stage.parent.parent),
               'prefix=' + str(Path('/') / args.stage.relative_to(args.stage.parent.parent)),
               'headersdir=' + str(args.stage / 'include/bash'), 'CC=' + str(args.cc)]
    result = subprocess.run(command, cwd=args.work, capture_output=True, text=True, timeout=120)
    (args.work / 'build.log').write_text(result.stdout + result.stderr)
    result.check_returncode()
    result = subprocess.run([str(args.readelf), '-h', str(args.work / 'example')], capture_output=True, text=True, check=True)
    (args.work / 'elf.log').write_text(result.stdout + result.stderr)
    assert 'AArch64' in result.stdout and 'DYN' in result.stdout
    print('PASS: clean target metadata and actual installed loadable sample builds AArch64 shared object')


if __name__ == '__main__':
    main()

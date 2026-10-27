#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Compile and consume a real libtool archive.
import argparse
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('libtool', 'cc', 'ar', 'work'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    if not args.work.is_absolute() or args.work.exists():
        parser.error('--work must be a new absolute directory')
    args.work.mkdir()
    work = args.work.resolve()
    (work / 'probe.c').write_text('int probe(void) { return 42; }\n')
    (work / 'main.c').write_text('int probe(void); int main(void) { return probe() == 42 ? 0 : 1; }\n')
    commands = [
        [str(args.libtool), '--tag=CC', '--mode=compile', str(args.cc), '-c', 'probe.c', '-o', 'probe.lo'],
        [str(args.libtool), '--tag=CC', '--mode=link', str(args.cc), '-static', '-o', 'libprobe.la', 'probe.lo', '-rpath', str(work / 'lib')],
        [str(args.ar), 't', '.libs/libprobe.a'],
        [str(args.cc), 'main.c', '.libs/libprobe.a', '-o', 'consumer'],
        [str(work / 'consumer')],
    ]
    for index, command in enumerate(commands):
        result = subprocess.run(command, cwd=work, capture_output=True, text=True, timeout=120)
        (work / (str(index) + '.log')).write_text(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError(f'{command}: status {result.returncode}: {result.stderr}')
        if index == 2:
            assert 'probe.o' in result.stdout
    print('PASS: real libtool static archive, selected archive tool, executable consumer')


if __name__ == '__main__':
    main()

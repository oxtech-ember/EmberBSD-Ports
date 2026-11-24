#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check the stack available to the CMake build worker on Darwin."""
import argparse
from pathlib import Path
import platform
import resource
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('pkgsrc', 'makeconf', 'bmake', 'work'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--role', required=True, choices=('native', 'target', 'development'))
    parser.add_argument('--generator', required=True, choices=('make', 'ninja'))
    args = parser.parse_args()
    if platform.system() != 'Darwin':
        parser.error('this check requires a Darwin build host')
    soft, hard = resource.getrlimit(resource.RLIMIT_STACK)
    initial = min(8 * 1024 * 1024, soft) if soft != resource.RLIM_INFINITY else 8 * 1024 * 1024
    if hard != resource.RLIM_INFINITY and hard <= initial:
        parser.error('the hard stack limit must exceed the initial soft limit')
    package = 'devel/protobuf-devel' if args.role == 'development' else 'devel/protobuf'
    cross = 'no' if args.role == 'native' else 'yes'
    with tempfile.TemporaryDirectory(dir=args.work.resolve()) as temp:
        source = Path(temp)
        build = source / 'cmake-pkgsrc-build'
        build.mkdir()
        # Use the actual worker selected by devel/cmake/build.mk.
        command = 'ulimit -s > soft-limit && ulimit -H -s > hard-limit'
        if args.generator == 'make':
            (build / 'Makefile').write_text('all:\n\t@' + command + '\n')
        else:
            (build / 'build.ninja').write_text('rule probe\n  command = ' + command + '\nbuild all: probe\n')
        resource.setrlimit(resource.RLIMIT_STACK, (initial, hard))
        try:
            subprocess.run([args.bmake.resolve(), '-C', args.pkgsrc.resolve() / package,
                            'MAKECONF=' + str(args.makeconf.resolve()), 'USE_CROSS_COMPILE=' + cross,
                            'CMAKE_GENERATOR=' + args.generator, 'WRKSRC=' + str(source),
                            'BUILD_DIRS=.', 'BUILD_TARGET=all', 'do-build'], check=True)
        finally:
            resource.setrlimit(resource.RLIMIT_STACK, (soft, hard))
        observed = (build / 'soft-limit').read_text().strip()
        expected = (build / 'hard-limit').read_text().strip()
        if observed != expected or observed == str(initial // 1024):
            raise SystemExit(f'{package}: initial {initial // 1024} KiB, worker {observed}, hard limit {expected}')
        print(f'{package} ({args.generator}): worker stack limit {observed}')


if __name__ == '__main__':
    main()

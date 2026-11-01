#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check that Rust build prerequisites apply only to build goals."""

import argparse
from pathlib import Path
import subprocess
import tempfile


SOURCE_GOALS = (
    'fetch', 'checksum', 'checksum-phase', 'makesum', 'makepatchsum',
    'distinfo', 'fetch-list', 'fetch-list-one-package',
    'fetch-list-recursive', 'mirror-distfiles', 'show-distfiles',
    'depends-fetch', 'depends-checksum', 'show-var', 'show-vars',
)
REQUIRED_INPUTS = (
    'EMBERBSD_SDK_SOURCE', 'EMBERBSD_RUST_COMPILER_PREFIX',
    'EMBERBSD_RUST_TARGET_SYSROOT', 'EMBERBSD_RUST_MACOS_SDK',
    'EMBERBSD_RUST_MACOS_MINIMUM', 'EMBERBSD_RUST_LOCK_ROOT',
    'EMBERBSD_RUST_LINK_CONTEXT', 'EMBERBSD_RUST_CROSS_TOOLS',
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bmake', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--producer', type=Path, default=Path(__file__).with_name('llvm-producer.mk'))
    args = parser.parse_args()
    bmake = args.bmake.resolve(strict=True)
    producer = args.producer.resolve(strict=True)
    work = args.work.resolve(strict=True)

    with tempfile.TemporaryDirectory(dir=work) as tmp:
        makefile = Path(tmp) / 'goal-policy.mk'
        gcc_inputs = ('EMBERBSD_RUST_CROSS_TOOLS', 'EMBERBSD_RUST_TARGET_SYSROOT')
        targets = (*SOURCE_GOALS, 'configure', 'build', 'package', 'install', 'custom-build')
        lines = ['MACHINE_ARCH= aarch64', 'RUST_STD_TARGET= aarch64',
                 f'.include "{producer}"',
                 '_GCC_REQUIRED_INPUTS= ' + ' '.join(gcc_inputs),
                 '.if ${_EMBERBSD_RUST_NEEDS_BUILD_INPUTS} == "yes"',
                 '.for var in ${_GCC_REQUIRED_INPUTS}',
                 '.if empty(${var}:U)', 'PKG_FAIL_REASON+= "Set ${var}."', '.endif',
                 '.endfor', '.endif', '.PHONY: all ' + ' '.join(targets)]
        makefile.write_text('\n'.join(lines) + '\n', encoding='utf-8')

        def missing(*goals):
            completed = subprocess.run(
                [str(bmake), '-f', str(makefile), '-V', '${PKG_FAIL_REASON}', *goals],
                cwd=tmp, text=True, capture_output=True, check=False)
            if completed.returncode:
                raise SystemExit(f'bmake failed for {goals!r}: {completed.stderr.strip()}')
            return completed.stdout.strip()

        for goal in SOURCE_GOALS:
            if missing(goal):
                raise SystemExit(f'{goal} unexpectedly requires build inputs')
        for goals in ((), ('all',), ('configure',), ('build',), ('package',),
                      ('install',), ('custom-build',), ('fetch', 'configure'),
                      ('checksum', 'build')):
            reasons = missing(*goals)
            found = {name for name in REQUIRED_INPUTS if name in reasons}
            if found != set(REQUIRED_INPUTS):
                raise SystemExit(f'{goals!r} did not retain build input guards: {sorted(found)}')

    print('PASS: metadata and source goals do not require Rust build inputs')
    print('PASS: default, build, unknown and mixed goals retain all input guards')


if __name__ == '__main__':
    main()

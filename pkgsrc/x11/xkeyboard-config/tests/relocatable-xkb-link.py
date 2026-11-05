#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Check the installed legacy XKB link in two DESTDIR prefixes."""

import argparse
import os
from pathlib import Path
import subprocess
import sys


PREFIXES = {
    'native-shaped': '/opt/emberbsd/aarch64',
    'usr-pkg': '/usr/pkg',
}


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--meson', required=True, type=Path)
    parser.add_argument('--ninja', required=True, type=Path)
    parser.add_argument('--source', required=True, type=Path,
                        help='patched xkeyboard-config source directory')
    parser.add_argument('--work', required=True, type=Path,
                        help='new absolute work directory')
    return parser.parse_args()


def check_link(destdir, prefix):
    destdir = destdir.resolve(strict=True)
    prefix = Path(prefix.lstrip('/'))
    link = destdir / prefix / 'share/X11/xkb'
    target = os.readlink(link)
    if os.path.isabs(target):
        raise RuntimeError(f'absolute legacy XKB link: {target}')

    resolved = (link.parent / target).resolve(strict=True)
    expected = (destdir / prefix / 'share/xkeyboard-config-2').resolve(strict=True)
    try:
        resolved.relative_to(destdir)
    except ValueError as error:
        raise RuntimeError(f'legacy XKB link escapes DESTDIR: {target}') from error
    if resolved != expected:
        raise RuntimeError(f'legacy XKB link resolves to {resolved}, expected {expected}')

    print(f'{link.relative_to(destdir)} -> {target}; resolves inside DESTDIR')


def main():
    args = parse_args()
    meson = args.meson.resolve(strict=True)
    ninja = args.ninja.resolve(strict=True)
    source = args.source.resolve(strict=True)
    work = args.work
    if not meson.is_file() or not os.access(meson, os.X_OK):
        raise SystemExit(f'Meson is not executable: {meson}')
    if not ninja.is_file() or not os.access(ninja, os.X_OK):
        raise SystemExit(f'Ninja is not executable: {ninja}')
    if not (source / 'meson.build').is_file():
        raise SystemExit(f'Meson source is missing: {source / "meson.build"}')
    if not work.is_absolute() or work.exists():
        raise SystemExit('WORK must be a new absolute directory')
    python = Path(sys.executable).resolve(strict=True)

    tools = work / 'tools'
    tools.mkdir(parents=True)
    (tools / 'python3').symlink_to(python)
    env = os.environ.copy()
    env['PATH'] = os.pathsep.join((
        str(tools), str(ninja.parent), str(meson.parent),
        env.get('PATH', os.defpath),
    ))

    for name, prefix in PREFIXES.items():
        build = work / f'build-{name}'
        destdir = work / f'destdir-{name}'
        subprocess.run(
            [str(meson), 'setup', str(build), str(source),
             '--prefix', prefix, '-Dxorg-rules-symlinks=true'],
            env=env, check=True,
        )
        subprocess.run([str(meson), 'compile', '-C', str(build)],
                       env=env, check=True)
        install_env = env.copy()
        install_env['DESTDIR'] = str(destdir)
        subprocess.run(
            [str(meson), 'install', '-C', str(build), '--no-rebuild'],
            env=install_env, check=True,
        )
        check_link(destdir, prefix)


if __name__ == '__main__':
    main()

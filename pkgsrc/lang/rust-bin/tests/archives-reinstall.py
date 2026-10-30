#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted rust-bin regression.
"""Check NetBSD archive checksums and that do-install can be repeated.

The NetBSD-provided archives must be in distinfo, and regenerating distinfo
on any build host must keep them. do-install removes the installer manifests
after installing; a second install into the same DESTDIR, after a failed
post-install, must not meet a component list without manifests.
"""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('pkgsrc', 'makeconf', 'bmake', 'shell'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    recipe = args.pkgsrc / 'lang/rust-bin'
    failures = []
    with tempfile.TemporaryDirectory(prefix='rust-bin-') as temporary:
        work = Path(temporary).resolve()
        base = [str(args.bmake), '-m', str(args.bmake.parent.parent / 'share/mk'),
                'SHELL=' + str(args.shell), 'MAKECONF=' + str(args.makeconf),
                'USE_CROSS_COMPILE=no', 'WRKOBJDIR=' + str(work / 'objects')]

        def run(*argv):
            proc = subprocess.run([*base, *argv], cwd=recipe, capture_output=True, text=True)
            return proc.returncode, (proc.stdout + proc.stderr).strip()

        def value(*argv):
            status, output = run(*argv)
            if status:
                sys.exit('bmake %s failed:\n%s' % (' '.join(argv), output[-2000:]))
            return output

        distinfo = (recipe / 'distinfo').read_text()
        version = value('-V', '${PKGVERSION_NOREV}')
        platforms = [p for p in value('-V', '${ONLY_FOR_PLATFORM}').split()
                     if p.startswith('NetBSD-')]
        if len(platforms) < 7:
            failures.append('NetBSD platforms: %s' % platforms)
        netbsd = []
        for platform in platforms:
            system, _, arch = platform.split('-')
            files = value('MACHINE_PLATFORM=%s-11.0-%s' % (system, arch),
                          '-V', '${DISTFILES}').split()
            if len(files) != 1 or not files[0].startswith('rust-%s-' % version):
                failures.append('%s selects %s' % (platform, files))
                continue
            netbsd.append(files[0])
            for algorithm in ('SHA256', 'Size'):
                entry = '%s (rust-bin-%s/%s) = ' % (algorithm, version, files[0])
                if entry not in distinfo:
                    failures.append('distinfo lacks ' + entry.rstrip(' ='))
        regenerated = value('-V', '${DISTFILES}', 'distinfo').split()
        for name in sorted(set(netbsd) - set(regenerated)):
            failures.append('distinfo target drops ' + name)

        # A minimal rust-installer image with one component.
        source = work / 'src'
        (source / 'rustc/bin').mkdir(parents=True)
        (source / 'rustc/bin/rustc').write_text('#!/bin/sh\n')
        (source / 'rustc/manifest.in').write_text('file:bin/rustc\n')
        (source / 'components').write_text('rustc\n')
        (source / 'rust-installer-version').write_text('3\n')
        destdir = work / 'destdir'
        prefix = value('-V', '${PREFIX}')
        installed = destdir / prefix.lstrip('/') / 'bin/rustc'
        install = ['WRKSRC=' + str(source), 'DESTDIR=' + str(destdir),
                   'RUST_ARCH=none', 'do-install']
        # do-install runs pax and bash from the tools directory.
        status, output = run('WRKSRC=' + str(source), 'tools')
        if status:
            sys.exit('tools failed:\n' + output[-2000:])
        # The second run repeats the bulk build after a failed post-install.
        for attempt in ('first', 'repeated'):
            status, output = run(*install)
            if status or not installed.is_file():
                failures.append('%s do-install failed:\n%s' % (attempt, output[-1500:]))
                break
    if failures:
        print('FAIL:\n' + '\n'.join(failures))
        return 1
    print('PASS: rust-bin %s NetBSD archives in distinfo, repeatable do-install' % version)
    return 0


if __name__ == '__main__':
    sys.exit(main())

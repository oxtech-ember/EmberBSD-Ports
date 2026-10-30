#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted Go bootstrap seed regression.
"""Check the go-bin seed version, host platform archives, and go127 selection."""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('pkgsrc', 'makeconf', 'bmake', 'shell'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    seed = args.pkgsrc / 'lang/go-bin'
    go = args.pkgsrc / 'lang/go127'
    with tempfile.TemporaryDirectory(prefix='go-seed-') as temporary:
        work = Path(temporary)
        base = [str(args.bmake), '-m', str(args.bmake.parent.parent / 'share/mk'),
                'SHELL=' + str(args.shell), 'MAKECONF=' + str(args.makeconf),
                'USE_CROSS_COMPILE=no', 'WRKOBJDIR=' + str(work / 'objects')]

        def query(recipe, *argv):
            proc = subprocess.run([*base, *argv], cwd=recipe, capture_output=True, text=True)
            assert proc.returncode == 0, (recipe, argv, proc.stdout, proc.stderr)
            return proc.stdout.strip()

        # One version: the seed is the Go release that lang/go127 builds.
        version = query(go, '-V', '${GO127_VERSION}')
        assert query(seed, '-V', '${PKGVERSION_NOREV}') == version, version

        # Every supported build host selects exactly its own archive, and
        # distinfo records that archive with its size.
        distinfo = (seed / 'distinfo').read_text()
        platforms = query(seed, '-V', '${ONLY_FOR_PLATFORM}').split()
        assert len(platforms) >= 8, platforms
        names = {'aarch64': 'arm64', 'x86_64': 'amd64'}
        for platform in platforms:
            system, _, arch = platform.split('-')
            machine = system + '-1.0-' + arch
            files = query(seed, 'MACHINE_PLATFORM=' + machine, '-V', '${DISTFILES}').split()
            expected = 'go%s.%s-%s.tar.gz' % (version, system.lower(), names[arch])
            assert files == [expected], (platform, files)
            for algorithm in ('BLAKE2s', 'SHA512', 'Size'):
                assert re.search('^%s \\(%s\\) = ' % (algorithm, re.escape(expected)),
                                 distinfo, re.M), (algorithm, expected)
        # The distinfo target sees all archives, so makesum keeps every host.
        listed = re.findall(r'^Size \((go[^)]+)\)', distinfo, re.M)
        assert len(listed) == len(platforms), (listed, platforms)

        # Without an installed go127, the source build depends on the seed.
        toolbase = work / 'toolbase'
        toolbase.mkdir()
        fresh = query(go, 'TOOLBASE=' + str(toolbase), '-V', '${GOROOT_BOOTSTRAP}',
                      '-V', '${TOOL_DEPENDS}')
        root, depends = fresh.splitlines()
        assert root == str(toolbase / 'go-bin'), root
        assert 'go-bin>=%s:../../lang/go-bin' % version in depends.split(), depends

        # An installed go127 is reused and the seed is not pulled in.
        (toolbase / 'go127/bin').mkdir(parents=True)
        (toolbase / 'go127/bin/go').write_text('')
        reuse = query(go, 'TOOLBASE=' + str(toolbase), '-V', '${GOROOT_BOOTSTRAP}',
                      '-V', '${TOOL_DEPENDS}')
        root, depends = (reuse + '\n').split('\n')[:2]
        assert root == str(toolbase / 'go127'), root
        assert 'lang/go-bin' not in depends, depends

        # An explicit seed always wins.
        explicit = query(go, 'TOOLBASE=' + str(toolbase), 'GOROOT_BOOTSTRAP=/explicit',
                         '-V', '${GOROOT_BOOTSTRAP}')
        assert explicit == '/explicit', explicit
    print('PASS: one-version seed, per-host archives, go127 seed selection')


if __name__ == '__main__':
    main()

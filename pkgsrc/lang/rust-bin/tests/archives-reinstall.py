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

        # A minimal rust-installer image with the compiler/runtime and the two
        # large optional documentation components. The names intentionally
        # overlap: rust-docs-json-preview must be removed before rust-docs.
        source = work / 'src'
        files = {
            'rustc/bin/rustc': '#!/bin/sh\n',
            'rustc/bin/rustdoc': '#!/bin/sh\n',
            'rustc/share/doc/rust/licenses/LICENSE': 'license\n',
            'rust-std-aarch64-apple-darwin/lib/rustlib/aarch64-apple-darwin/lib/libstd.rlib': 'std\n',
            'cargo/bin/cargo': '#!/bin/sh\n',
            'cargo/share/doc/cargo/LICENSE': 'cargo license\n',
            'rust-docs/share/doc/rust/html/index.html': 'html docs\n',
            'rust-docs-json-preview/share/doc/rust/json/index.json': '{}\n',
        }
        for relative, contents in files.items():
            path = source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(contents)
        manifests = {
            'rustc': ('file:bin/rustc\nfile:bin/rustdoc\n'
                      'file:share/doc/rust/licenses/LICENSE\n'),
            'rust-std-aarch64-apple-darwin':
                'file:lib/rustlib/aarch64-apple-darwin/lib/libstd.rlib\n',
            'cargo': 'file:bin/cargo\nfile:share/doc/cargo/LICENSE\n',
            'rust-docs': 'dir:share/doc/rust/html\n',
            'rust-docs-json-preview': 'dir:share/doc/rust/json\n',
        }
        for component, manifest in manifests.items():
            (source / component / 'manifest.in').write_text(manifest)
        (source / 'components').write_text('\n'.join(manifests) + '\n')
        (source / 'rust-installer-version').write_text('3\n')
        destdir = work / 'destdir'
        prefix = value('-V', '${PREFIX}')
        installed_prefix = destdir / prefix.lstrip('/')
        installed = [installed_prefix / path for path in (
            'bin/rustc', 'bin/rustdoc', 'bin/cargo',
            'lib/rustlib/aarch64-apple-darwin/lib/libstd.rlib',
            'share/doc/rust/licenses/LICENSE', 'share/doc/cargo/LICENSE')]
        docs = [installed_prefix / 'share/doc/rust/html/index.html',
                installed_prefix / 'share/doc/rust/json/index.json']
        install = ['WRKSRC=' + str(source), 'DESTDIR=' + str(destdir),
                   'RUST_ARCH=aarch64-apple-darwin', 'do-install']
        # do-install runs pax and bash from the tools directory.
        status, output = run('WRKSRC=' + str(source), 'tools')
        if status:
            sys.exit('tools failed:\n' + output[-2000:])
        # The second run repeats the bulk build after a failed post-install.
        for attempt in ('first', 'repeated'):
            status, output = run(*install)
            if status or not all(path.is_file() for path in installed):
                failures.append('%s do-install failed:\n%s' % (attempt, output[-1500:]))
                break
            if any(path.exists() for path in docs):
                failures.append('%s default install retained optional docs' % attempt)
                break

        docs_destdir = work / 'docs-destdir'
        docs_prefix = docs_destdir / prefix.lstrip('/')
        docs_install = ['PKG_OPTIONS.rust-bin=doc',
                        'WRKSRC=' + str(source), 'DESTDIR=' + str(docs_destdir),
                        'RUST_ARCH=aarch64-apple-darwin', 'do-install']
        status, output = run(*docs_install)
        if status or not all((docs_prefix / path).is_file() for path in (
                'bin/rustc', 'bin/rustdoc', 'bin/cargo',
                'lib/rustlib/aarch64-apple-darwin/lib/libstd.rlib',
                'share/doc/rust/licenses/LICENSE', 'share/doc/cargo/LICENSE',
                'share/doc/rust/html/index.html', 'share/doc/rust/json/index.json')):
            failures.append('docs option install failed or omitted package payload:\n%s' %
                            output[-1500:])
    if failures:
        print('FAIL:\n' + '\n'.join(failures))
        return 1
    print('PASS: rust-bin %s NetBSD archives, repeatable default install without docs, '
          'and opt-in docs payload' % version)
    return 0


if __name__ == '__main__':
    sys.exit(main())

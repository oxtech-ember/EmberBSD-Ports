#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), actual Libtool provider metadata controls.
"""Check required provider patterns without installing or replacing packages."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


def require(value, message):
    if not value:
        raise ValueError(message)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ('pkgsrc', 'bmake', 'makeconf', 'pkg-admin', 'pkg-info', 'pkgdb', 'sandbox-profile', 'work'):
        cli.add_argument('--' + name, required=True, type=Path)
    cli.add_argument('--patch', type=Path, help='Apply the common floor patch to a private source copy')
    args = cli.parse_args()
    require(all(path.is_absolute() for path in vars(args).values() if path is not None), 'Use absolute paths')
    work = args.work
    work.mkdir()
    for name in ('home', 'tmp'):
        (work / name).mkdir()
    environment = dict(os.environ, LC_ALL='C', HOME=str(work / 'home'), TMPDIR=str(work / 'tmp'),
                       PKG_DBDIR=str(args.pkgdb))
    commands = []
    results = {}

    def run(name, argv, success=True):
        full = ['/usr/bin/sandbox-exec', '-f', str(args.sandbox_profile), *map(str, argv)]
        process = subprocess.run(full, env=environment, cwd=work, capture_output=True, timeout=45)
        (work / (name + '.out')).write_bytes(process.stdout)
        (work / (name + '.err')).write_bytes(process.stderr)
        commands.append(dict(name=name, argv=full, exit=process.returncode))
        (work / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        if success:
            require(process.returncode == 0, 'metadata command failed: ' + name)
        return process.returncode, process.stdout.decode()

    for variant in ('baseline', 'candidate'):
        tree = work / variant
        tree.mkdir()
        shutil.copytree(args.pkgsrc / 'mk', tree / 'mk', symlinks=True)
        for entry in args.pkgsrc.iterdir():
            if entry.name == 'mk':
                continue
            if entry.name not in ('converters', 'textproc'):
                (tree / entry.name).symlink_to(entry)
                continue
            directory = tree / entry.name
            directory.mkdir()
            for package in entry.iterdir():
                if package.name in ('libiconv', 'libunistring'):
                    shutil.copytree(package, directory / package.name, symlinks=True)
                else:
                    (directory / package.name).symlink_to(package)
        if variant == 'candidate' and args.patch:
            run('patch', [args.bmake.parent / 'nbpatch', '-f', '-N', '-F', '0', '-p1',
                          '-d', tree, '-i', args.patch])

    def native(variant, package):
        _, output = run(variant + '-' + package.replace('/', '-'),
            [args.bmake, '-C', work / variant / package, 'MAKECONF=' + str(args.makeconf),
             'WRKOBJDIR=' + str(work / 'objects'), 'PACKAGES=' + str(work / 'packages'),
             '-V', '${TOOL_DEPENDS}', '-V', '${LIBTOOL_REQD}'])
        rows = output.splitlines()
        require(len(rows) == 2, 'unexpected native metadata output')
        return rows[0].split(), rows[1]

    def patterns(dependencies, provider):
        return [dep.partition(':')[0] for dep in dependencies if dep.startswith(provider + '>=')]

    installed = args.pkgdb / 'libtool-base-2.6.2' / '+CONTENTS'
    require(installed.is_file(), 'The negative installed-provider fixture requires registered libtool-base-2.6.2')
    registered_hash = hashlib.sha256(installed.read_bytes()).hexdigest()
    for package in ('converters/libiconv', 'textproc/libunistring'):
        old, _ = native('baseline', package)
        new, floor = native('candidate', package)
        before = patterns(old, 'libtool-base')
        after = patterns(new, 'libtool-base')
        require(before and after, 'missing ordinary native Libtool dependency')
        old_status = [run('installed-before-' + package.replace('/', '-') + '-' + str(i),
                         [args.pkg_info, '-e', pattern], success=False)[0] for i, pattern in enumerate(before)]
        new_status = [run('installed-after-' + package.replace('/', '-') + '-' + str(i),
                         [args.pkg_info, '-e', pattern], success=False)[0] for i, pattern in enumerate(after)]
        require(all(status == 0 for status in old_status), 'baseline no longer reproduces the accepted old provider')
        require(any(status != 0 for status in new_status), 'ordinary consumer still accepts installed libtool-base-2.6.2')
        results[package] = dict(baseline=before, candidate=after, LIBTOOL_REQD=floor)

    def role(variant, label, cross, fortran, request=None, platform_request=None, autoreconf=False):
        makefile = work / (variant + '-' + label + '.mk')
        makefile.write_text('USE_LIBTOOL= yes\nUSE_LANGUAGES= c' + (' fortran' if fortran else '') + '\n'
            + 'USE_TOOLS= autoconf autoreconf\n' * autoreconf
            + 'USE_CROSS_COMPILE= ' + ('yes' if cross else 'no') + '\n'
            + 'LOCALBASE= /selected/native\nTOOLBASE= /selected/native\nWRAPPER_BINDIR= /selected/wrappers\n'
            + 'MACHINE_PLATFORM= NetBSD-11.0-aarch64\nTARGET_MACHINE_PLATFORM= NetBSD-11.0-aarch64\n'
            + '_PKGSRC_USE_MKTOOLS= no\nPKGPATH= regression/libtool\n'
            + (('LIBTOOL_REQD= ' + request + '\n') if request else '')
            + (('_OPSYS_LIBTOOL_REQD= ' + platform_request + '\n') if platform_request else '')
            + f'.include "{work / variant}/mk/bsd.pkg.use.mk"\n'
            + (f'.include "{work / variant}/mk/tools/autoconf.mk"\n' if autoreconf else ''))
        _, output = run(variant + '-' + label, [args.bmake, '-r', '-f', makefile,
            '-V', '${TOOL_DEPENDS}', '-V', '${LIBTOOL_REQD}', '-V', '${PKG_LIBTOOL}'])
        rows = output.splitlines()
        require(len(rows) == 3, 'unexpected role metadata output')
        return dict(dependencies=rows[0].split(), requested=rows[1], script=rows[2])

    match_cache = {}

    def matches(pattern, name):
        if (pattern, name) in match_cache:
            return match_cache[pattern, name]
        status, _ = run('pmatch-' + str(len(commands)), [args.pkg_admin, 'pmatch', pattern, name], success=False)
        require(status in (0, 1), 'pkg_admin returned a pattern error')
        match_cache[pattern, name] = status == 0
        return status == 0

    for cross in (False, True):
        for fortran in (False, True):
            label = ('cross' if cross else 'native') + ('-fortran' if fortran else '-c')
            provider = 'cross-libtool-base-NetBSD-11.0-aarch64' if cross else 'libtool-base'
            minimum = '2.6.2nb2' if cross else '2.6.2nb1'
            providers = [(provider, minimum)]
            if fortran:
                providers.append(('cross-libtool-fortran-NetBSD-11.0-aarch64' if cross else 'libtool-fortran', '2.6.2nb2'))
            for suffix, requested, platform_request in (('default', None, None), ('older', '2.4.2nb9', None),
                    ('strong', '99.0', None), ('platform-strong', '2.4.2nb9', '99.0'),
                    ('both', '99.0', '1.0')):
                key = label + '-' + suffix
                row = role('candidate', key, cross, fortran, requested, platform_request, autoreconf=cross)
                if cross:
                    providers_for_case = providers + [('libtool-base', '2.6.2nb1')]
                else:
                    providers_for_case = providers
                for name, version in providers_for_case:
                    required = patterns(row['dependencies'], name)
                    require(required, 'provider disappeared: ' + name)
                    require(len(required) == len(set(required)), 'duplicate provider constraint')
                    require(not all(matches(p, name + '-2.6.2') for p in required), 'old provider accepted: ' + key)
                    if version == '2.6.2nb2':
                        require(not all(matches(p, name + '-2.6.2nb1') for p in required), 'old provider revision accepted: ' + name)
                    expected = '100.0' if suffix in ('strong', 'platform-strong', 'both') else version
                    require(all(matches(p, name + '-' + expected) for p in required), 'compatible provider rejected: ' + key)
                    if suffix in ('strong', 'platform-strong', 'both'):
                        require(not all(matches(p, name + '-' + version) for p in required), 'higher request was lost: ' + key)
                if requested:
                    require(row['requested'] == requested, 'consumer requirement changed')
                results[key] = row
    require(hashlib.sha256(installed.read_bytes()).hexdigest() == registered_hash, 'installed package registration changed')
    (work / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
    print('PASS: ordinary libiconv/libunistring queries reject the registered old Libtool provider')
    print('PASS: native/cross C/Fortran and host autoreconf floors preserve stronger caller/platform requests')
    print('SCOPE: bmake/pkg_info/pkg_admin metadata only; no package or prefix mutation')


if __name__ == '__main__':
    main()

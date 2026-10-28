#!/usr/bin/env python3
"""Check the evaluated Texinfo source, roles and native/cross tool inputs."""
import argparse
import pathlib
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pkgsrc', type=pathlib.Path)
    parser.add_argument('makeconf', type=pathlib.Path)
    parser.add_argument('bmake', type=pathlib.Path)
    parser.add_argument('--cross', action='store_true')
    parser.add_argument('--package', choices=('devel/gtexinfo',
                                               'pkgtools/pkg_install-info'))
    args = parser.parse_args()
    variables = ['PKGNAME', 'DISTNAME', 'DISTINFO_FILE', 'PATCHDIR',
                 'BUILD_DIRS', 'INSTALL_DIRS', 'INSTALL_TARGET', 'TEST_DIRS',
                 'TEST_TARGET', 'CONFIGURE_ARGS', 'CONFIGURE_ENV', 'DEPENDS',
                 'PKG_SKIP_REASON', 'PKG_FAIL_REASON', 'MACHINE_GNU_PLATFORM',
                 'NATIVE_MACHINE_GNU_PLATFORM', 'NATIVE_CC', 'NATIVE_AR',
                 'NATIVE_RANLIB']
    rows = {}
    packages = [args.package] if args.package else [
        'devel/gtexinfo', 'pkgtools/pkg_install-info']
    for package in packages:
        command = [str(args.bmake), '-C', str(args.pkgsrc / package),
                   'MAKECONF=' + str(args.makeconf)]
        if not args.cross:
            command.append('USE_CROSS_COMPILE=no')
        for variable in variables:
            command += ['-V', '${' + variable + '}']
        result = subprocess.run(command, check=True, text=True,
                                stdout=subprocess.PIPE, timeout=180)
        values = result.stdout.splitlines()
        assert len(values) == len(variables), result.stdout
        row = dict(zip(variables, values))
        assert not row['PKG_SKIP_REASON'], row['PKG_SKIP_REASON']
        assert not row['PKG_FAIL_REASON'], row['PKG_FAIL_REASON']
        assert row['DISTNAME'] == 'texinfo-7.3', row
        assert row['PKGNAME'] == ('gtexinfo-7.3nb9' if package == 'devel/gtexinfo' else 'pkg_install-info-7.3nb3'), row
        for variable, name in [('DISTINFO_FILE', 'distinfo'), ('PATCHDIR', 'patches')]:
            assert pathlib.Path(row[variable]).resolve() == (
                args.pkgsrc / 'devel/gtexinfo' / name).resolve(), row
        if args.cross:
            assert '--host=' + row['MACHINE_GNU_PLATFORM'] in row['CONFIGURE_ARGS']
            assert '--build=' + row['NATIVE_MACHINE_GNU_PLATFORM'] in row['CONFIGURE_ARGS']
            for name in ('CC', 'AR', 'RANLIB'):
                assert row['NATIVE_' + name], row
                assert 'BUILD_' + name + '=' in row['CONFIGURE_ENV'], row
                assert row['NATIVE_' + name].split()[0] in row['CONFIGURE_ENV'], row
        rows[package] = row
    if 'pkgtools/pkg_install-info' in rows:
        standalone = rows['pkgtools/pkg_install-info']
        assert [pathlib.Path(p).name for p in standalone['BUILD_DIRS'].split()] == ['lib', 'install-info']
        assert pathlib.Path(standalone['INSTALL_DIRS']).name == 'install-info'
        assert standalone['INSTALL_TARGET'] == 'install-exec'
        assert pathlib.Path(standalone['TEST_DIRS']).name == 'install-info'
        assert standalone['TEST_TARGET'] == 'check'
        assert not any(word in standalone['DEPENDS'] for word in ('perl', 'gtexinfo', 'p5-'))
    if 'devel/gtexinfo' in rows:
        assert '--enable-perl-xs' in rows['devel/gtexinfo']['CONFIGURE_ARGS']
    mode = 'cross' if args.cross else 'native'
    print('Texinfo 7.3 metadata pass (' + mode + '): ' + ', '.join(packages))


if __name__ == '__main__':
    main()

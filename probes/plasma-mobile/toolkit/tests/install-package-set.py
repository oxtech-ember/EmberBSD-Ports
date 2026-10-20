#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Python migration of the native installer fixture.
"""Check production shell helpers with real packages in private host prefixes."""
import sys
sys.dont_write_bytecode = True
import os
from pathlib import Path
import re
import shlex
import shutil

sys.path.insert(0, str(Path(__file__).resolve().parent))
from package_set_fixture import Fixture, check, metadata


def main(argv):
    f = Fixture(argv)
    add = os.environ.get('PKG_ADD', 'pkg_add')
    payload = f.work / 'payload'; (payload / 'share/installer-test').mkdir(parents=True)
    valid = f.work / 'valid'; (valid / 'packages').mkdir(parents=True)
    names = ('installer-leaf-1.0', 'installer-root-1.0')
    for name in names:
        file = 'share/installer-test/' + name
        (payload / file).write_text(name + '\n')
        archive = f.package(f.work / name, name, payload, [file],
                            dependencies='installer-leaf>=1.0' if name == names[-1] else None)
        shutil.copy2(archive, valid / 'packages' / archive.name)
    (valid / 'install-order.txt').write_text(''.join(name + '.tgz\n' for name in names))
    (valid / 'roots.txt').write_text(names[-1] + '\n')
    (valid / 'target.txt').write_bytes(metadata('aarch64'))
    from emberbsd_sdk.inventory import sha256_file
    (valid / 'packages.sha256').write_text(''.join(
        sha256_file(valid / 'packages' / (name + '.tgz')) + '  packages/' + name + '.tgz\n' for name in names))
    env = dict(f.env, PKG_ADD=add)

    def verify(name, directory, expected=None, install=False):
        log = f.work / (name + '-install.log')
        command = ['sh', f.installer, *(['--install', directory, log] if install else [directory])]
        result = f.status(command, env=env)
        text = result.stdout + result.stderr; (f.work / (name + '.log')).write_bytes(text)
        if expected:
            check(result.returncode != 0 and expected.encode() in text, f'{name} did not reject {expected}: {text!r}')
        else:
            check(result.returncode == 0, f'{name}: {text!r}')
            check(b'2 archives, SHA256, target metadata, roots and dependency order verified' in text,
                  'Verification did not check dependency order')
        check(not log.exists(), name + ' reached the installation mutation')
        f.count += 1; print('PASS: ' + name)

    def mutate(name, expected, change):
        directory = f.work / name; shutil.copytree(valid, directory)
        change(directory)
        verify(name, directory, expected)
        if sys.platform == 'darwin':
            verify(name + '-before-install', directory, expected, True)

    def append(path, data):
        with path.open('ab') as stream: stream.write(data)

    verify('default-verify', valid)
    mutate('corrupt-hash', 'SHA256 mismatch', lambda d: append(d / 'packages' / (names[0] + '.tgz'), b'changed'))
    mutate('missing-target-receipt', 'Missing regular target.txt', lambda d: (d / 'target.txt').unlink())
    mutate('wrong-target-receipt', 'Target receipt mismatch', lambda d: (d / 'target.txt').write_bytes(metadata('x86_64')))
    mutate('missing-archive', 'Package directory and installation manifest differ', lambda d: (d / 'packages' / (names[0] + '.tgz')).unlink())
    mutate('reversed-order', 'Invalid dependency order', lambda d: (d / 'install-order.txt').write_text(''.join(n + '.tgz\n' for n in reversed(names))))
    mutate('duplicate-order', 'Invalid or duplicate install-order', lambda d: append(d / 'install-order.txt', (names[0] + '.tgz\n').encode()))
    mutate('extra-archive', 'Package directory and installation manifest differ', lambda d: shutil.copyfile(d / 'packages' / (names[0] + '.tgz'), d / 'packages/unlisted-1.0.tgz'))
    mutate('missing-root', 'Invalid, missing or duplicate root', lambda d: (d / 'roots.txt').write_text('missing-root-1.0\n'))
    mutate('unfinished-manifest', 'Manifest needs a final newline', lambda d: (d / 'packages.sha256').write_bytes((d / 'packages.sha256').read_bytes().removesuffix(b'\n')))
    mock_bin = f.work / 'bsd-od-bin'; mock_bin.mkdir()
    real_od = os.fsdecode(f.run(['sh', '-c', 'command -v od'])).strip()
    mock = mock_bin / 'od'
    mock.write_text('#!/bin/sh\nset -eu\ncase "$*" in\n' +
        "  '-An -tu1') " + shlex.quote(real_od) + ' "$@" | awk \'{ for (i=1; i<=NF; i++) printf " %03d", $i; print "" }\' ;;\n' +
        '  *) exec ' + shlex.quote(real_od) + ' "$@" ;;\nesac\n')
    mock.chmod(0o755)
    env['PATH'] = str(mock_bin) + os.pathsep + os.environ['PATH']
    verify('bsd-od-final-lf', valid)
    production = f.installer.read_text()
    control = production.replace(" | sed 's/^0*//'", '', 1)
    check(control != production, 'Missing production decimal normalization')
    legacy = f.work / 'installer-decimal-control.sh'; legacy.write_text(control)
    result = f.status(['sh', legacy, valid], env=env)
    text = result.stdout + result.stderr; (f.work / 'bsd-od-decimal-control.log').write_bytes(text)
    check(result.returncode != 0 and b'Manifest needs a final newline' in text, 'Decimal control did not reject 010')
    f.count += 1; print('PASS: bsd-od-decimal-control rejects the valid LF bundle')
    for manifest, error in {'packages.sha256': 'Invalid or duplicate checksum entry',
                            'install-order.txt': 'Invalid or duplicate install-order entry',
                            'roots.txt': 'Invalid, missing or duplicate root package'}.items():
        mutate('bsd-od-no-lf-' + manifest, 'Manifest needs a final newline',
               lambda d, m=manifest: (d / m).write_bytes((d / m).read_bytes().removesuffix(b'\n')))
        mutate('bsd-od-crlf-' + manifest, error,
               lambda d, m=manifest: (d / m).write_bytes((d / m).read_bytes().replace(b'\n', b'\r\n')))
    env['PATH'] = os.environ['PATH']
    def archive_link(directory):
        path = directory / 'packages' / (names[0] + '.tgz')
        path.unlink(); path.symlink_to(valid / 'packages' / path.name)
    mutate('archive-symlink', 'Not a regular package archive', archive_link)
    if sys.platform == 'darwin':
        verify('host-install-rejected', valid, 'Installation requires an EmberBSD target', True)

    # These are exact production helpers. Only their storage paths are private.
    helper_match = re.search(r'^install_archive\(\) \{\n.*?^\}', production, re.M | re.S)
    policy_match = re.search(r'^install_package\(\) \(\n.*?^\)', production, re.M | re.S)
    check(helper_match is not None and policy_match is not None, 'Missing production installation helpers')
    helper, policy = helper_match[0], policy_match[0]
    check('install_package "${archive%.tgz}" "$bundle/packages/$archive"' in production,
          'Install loop does not call the package-mark helper')
    raw = f.run([f.info, '-q', '-B', os.environ.get('PKG_HOST_SAMPLE', 'digest')])
    host_metadata = b''.join(line + b'\n' for line in raw.splitlines() if re.match(rb'^(OPSYS|OS_VERSION|MACHINE_ARCH|OBJECT_FMT)=', line))
    check(len(host_metadata.splitlines()) == 4, 'Incomplete native package metadata')
    native_name, native_file = 'installer-mask-1.0', 'share/installer-mask/nested/data'
    (payload / native_file).parent.mkdir(parents=True)
    (payload / native_file).write_text('umask acceptance\n')
    script = b'#!/bin/sh\nset -eu\ncase $2 in POST-INSTALL) printf \'install script ran\\n\' > "$PKG_PREFIX/share/installer-mask/script-ran" ;; esac\n'
    native_archive = f.package(f.work / 'native-mask-package', native_name, payload, [native_file],
                               build=host_metadata, scripts={'+INSTALL': script})

    def area_paths(label):
        area = f.work / label
        prefix, database = area / 'prefix', area / 'pkgdb'
        prefix.mkdir(parents=True); database.mkdir()
        config = area / 'pkg_install.conf'
        config.write_text(f'PKG_DBDIR={database}\nPKG_REFCOUNT_DBDIR={area}/refcount\n')
        return area, prefix, database, config, area / 'run.sh'

    for label in ('control', 'fixed'):
        area, prefix, database, config, runner = area_paths('umask-' + label)
        body = '#!/bin/sh\nset -eu\numask 077\nadd=$1\nshift\n'
        body += helper + '\ninstall_archive "$@"\n' if label == 'fixed' else '"$add" -U "$@"\n'
        runner.write_text(body)
        result = f.status(['sh', runner, add, '-C', config, '-K', database, '-p', prefix, native_archive])
        text = result.stdout + result.stderr; (area / 'install.log').write_bytes(text)
        check(result.returncode == 0, f'Private native installation failed: {text!r}')
        mode = (prefix / 'share/installer-mask/nested').stat().st_mode & 0o777
        check(mode == (0o755 if label == 'fixed' else 0o700), f'Unexpected umask mode: {mode:o}')
        check((prefix / native_file).read_bytes() == b'umask acceptance\n', 'Installed private payload differs')
        check((prefix / 'share/installer-mask/script-ran').read_bytes() == b'install script ran\n', 'Package install script was skipped')
        f.run([f.admin, '-C', config, '-K', database, 'check', native_name])
        f.count += 1; print(f'PASS: native-umask-{label} ({mode:o})')

    bases = ('installer-policy-manual', 'installer-policy-auto', 'installer-policy-root')
    archives = {}
    for version in ('1.0', '2.0'):
        for base in bases:
            name = base + '-' + version; file = 'share/installer-policy/' + base
            (payload / file).parent.mkdir(parents=True, exist_ok=True); (payload / file).write_text(name + '\n')
            archives[name] = f.package(f.work / name, name, payload, [file], build=host_metadata,
                dependencies=' '.join(b + '>=1.0' for b in bases[:2]) if base == bases[-1] else None)

    def policy_area(label):
        area, prefix, database, config, runner = area_paths('marks-' + label)
        runner.write_text('''#!/bin/sh
set -eu
umask 077
add_tool=$1; info_tool=$2; admin_tool=$3; work=$4; shift 4
fixture_add() { "$add_tool" -C "$work/pkg_install.conf" -K "$work/pkgdb" -p "$work/prefix" "$@"; }
fixture_info() { "$info_tool" -K "$work/pkgdb" "$@"; }
fixture_admin() { "$admin_tool" -C "$work/pkg_install.conf" -K "$work/pkgdb" "$@"; }
add=fixture_add; info=fixture_info; admin=fixture_admin
''' + helper + '\n' + policy + '''
for archive do
    name=${archive##*/}
    install_package "${name%.tgz}" "$archive" || exit
done
''')
        return area, prefix, database, config, runner

    def verify_policy(area, prefix, database, config, version, expected):
        for base, automatic in zip(bases, expected):
            name = base + '-' + version
            actual = f.run([f.info, '-K', database, '-q', '-Q', 'automatic', name]).strip().lower()
            check((actual == b'yes') == automatic, f'{name}: wrong automatic mark {actual!r}')
            check((prefix / 'share/installer-policy' / base).read_text() == name + '\n', name + ': payload differs')
            (area / (name + '-mark.txt')).write_bytes(b'automatic=' + actual + b'\n')
        f.run([f.admin, '-C', config, '-K', database, 'check', *(base + '-' + version for base in bases)])

    def install_policy(area, runner, version, label):
        (area / 'roots.txt').write_text(bases[-1] + '-' + version + '\n')
        result = f.status(['sh', runner, add, f.info, f.admin, area, *(archives[base + '-' + version] for base in bases)])
        text = result.stdout + result.stderr; (area / (label + '.log')).write_bytes(text)
        check(result.returncode == 0, f'Package-mark installation failed: {text!r}')

    area, prefix, database, config, runner = policy_area('fresh')
    install_policy(area, runner, '1.0', 'install')
    verify_policy(area, prefix, database, config, '1.0', (True, True, False))
    f.count += 1; print('PASS: native-marks-first-install (new dependencies automatic, root manual)')
    area, prefix, database, config, runner = policy_area('existing')
    for index, base in enumerate(bases):
        f.run([add, '-C', config, '-K', database, '-p', prefix, *(['-A'] if index else []), archives[base + '-1.0']])
    verify_policy(area, prefix, database, config, '1.0', (False, True, True))
    install_policy(area, runner, '2.0', 'upgrade')
    verify_policy(area, prefix, database, config, '2.0', (False, True, False))
    f.count += 1; print('PASS: native-marks-upgrade (existing manual/automatic preserved, automatic root promoted)')
    f.run([f.admin, '-C', config, '-K', database, 'set', 'automatic=yes', bases[-1] + '-2.0'])
    install_policy(area, runner, '2.0', 'reinstall')
    verify_policy(area, prefix, database, config, '2.0', (False, True, False))
    f.count += 1; print('PASS: native-marks-reinstall (existing manual/automatic preserved, automatic root promoted)')
    print(f'PASS: {f.count} installer checks with native pkgtools and real package archives; no target installation (native fixtures use private prefixes)')


if __name__ == '__main__':
    main(sys.argv[1:])

#!/usr/bin/env python3
"""Exercise wx configure's cross-root pkg-config inference with real pkg-config.
Origin: EmberBSD (AI-assisted). SPDX-License-Identifier: BSD-2-Clause
"""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--source', type=Path, required=True)
p.add_argument('--shell', required=True)
p.add_argument('--pkg-config', required=True)
p.add_argument('--work-parent', type=Path, required=True)
a = p.parse_args()

configure = (a.source / 'configure').read_text()
start = configure.index('if test "$build" != "$host" -a "$GCC" = yes')
end = configure.index('\n\ncat >confcache', start)
block = configure[start:end]

with tempfile.TemporaryDirectory(prefix='wx-pkgconfig-sysroot-',
                                 dir=a.work_parent) as tmp:
    work = Path(tmp)
    sysroot = work / 'sysroot'
    target_pc = sysroot / 'usr/pkg/lib/pkgconfig'
    host_root = work / 'host'
    host_pc = host_root / 'lib/pkgconfig'
    explicit_pc = work / 'explicit/pkgconfig'
    for directory in (target_pc, host_pc, explicit_pc):
        directory.mkdir(parents=True)

    def write_pc(path, prefix, marker):
        path.write_text(f'''prefix={prefix}
includedir=${{prefix}}/include/{marker}
Name: emberbsd-pkgconfig-sysroot-test
Description: controlled configure metadata selection
Version: 1
Cflags: -I${{includedir}}
Libs:
''')

    package = 'emberbsd-pkgconfig-sysroot-test'
    write_pc(target_pc / f'{package}.pc', '/usr/pkg', 'target')
    write_pc(host_pc / f'{package}.pc', str(host_root), 'host')
    write_pc(explicit_pc / f'{package}.pc', str(work / 'explicit'), 'explicit')

    cc = work / 'cc'
    cc.write_text('''#!SHELL
if [ "$1" = "-print-prog-name=ld" ]; then
    : > "$CC_QUERIED"
    printf '%s\\n' "$HOST_LD"
    exit 0
fi
exit 2
'''.replace('SHELL', a.shell))
    cc.chmod(0o755)

    driver = work / 'configure-cross-root.sh'
    driver.write_text('''exec 5>/dev/null
as_me=pkgconfig-sysroot
as_echo=echo
as_echo_n='printf %s'
build=$1
host=$2
GCC=yes
SEARCH_INCLUDE=/usr/include
SEARCH_LIB=/usr/lib
wx_cv_std_libpath=lib
wx_cv_std_libfullpath=/usr/lib
x_includes=/explicit/include
x_libraries=/explicit/lib
CC=$CC_SHIM
''' + block + '''
printf 'PATH=%s\\n' "$PKG_CONFIG_PATH"
"$PKG_CONFIG" --cflags emberbsd-pkgconfig-sysroot-test
''')

    def run(name, build, host, pkg_libdir, pkg_sysroot, pkg_path):
        queried = work / f'{name}.cc-queried'
        env = dict(os.environ)
        for key in ('PKG_CONFIG_PATH', 'PKG_CONFIG_SYSROOT_DIR',
                    'PKG_CONFIG_LIBDIR', 'PKG_CONFIG_TOP_BUILD_DIR'):
            env.pop(key, None)
        env.update({
            'CC_SHIM': str(cc),
            'CC_QUERIED': str(queried),
            'HOST_LD': str(host_root / 'bin/ld'),
            'PKG_CONFIG': a.pkg_config,
            'PKG_CONFIG_LIBDIR': str(pkg_libdir),
            'PKG_CONFIG_SYSROOT_DIR': str(pkg_sysroot) if pkg_sysroot else '',
            'PKG_CONFIG_PATH': pkg_path,
        })
        result = subprocess.run([a.shell, str(driver), build, host], cwd=work,
                                env=env, text=True, capture_output=True)
        assert result.returncode == 0, (name, result.stdout, result.stderr)
        lines = result.stdout.splitlines()
        assert len(lines) == 2, (name, result.stdout)
        return lines[0][len('PATH='):], lines[1], queried.exists()

    # Native configure must leave pkg-config selection alone and never query CC.
    native_path, native_flags, native_cc = run(
        'native', 'aarch64-apple-darwin', 'aarch64-apple-darwin',
        host_pc, '', '')
    assert native_path == '', native_path
    assert native_flags == f'-I{host_root}/include/host', native_flags
    assert not native_cc, 'native configure queried the cross linker'
    print('native selection PASS')

    # A declared sysroot is authoritative even if the cross compiler reports a
    # linker rooted in a conflicting host prefix. The old inference selects
    # host_pc through PKG_CONFIG_PATH and fails this target-only assertion.
    cross_path, cross_flags, cross_cc = run(
        'cross-sysroot', 'x86_64-apple-darwin', 'aarch64-unknown-netbsd',
        target_pc, sysroot, '')
    expected = f'-I{sysroot}/usr/pkg/include/target'
    assert cross_path == '', cross_path
    assert cross_flags == expected, (cross_flags, expected)
    assert not cross_cc, 'sysroot cross configure queried the host linker'
    print('cross declared sysroot with empty PKG_CONFIG_PATH PASS')

    # Retain the legacy cross-compiler fallback when no SDK sysroot is set.
    legacy_path, legacy_flags, legacy_cc = run(
        'cross-no-sysroot', 'x86_64-apple-darwin', 'aarch64-unknown-netbsd',
        target_pc, '', '')
    assert legacy_path == f'{host_root}/local/lib/pkgconfig:{host_pc}', legacy_path
    assert legacy_flags == f'-I{host_root}/include/host', legacy_flags
    assert legacy_cc, 'legacy cross configure did not query the linker shim'
    print('cross without sysroot preserves linker-root fallback PASS')

    # An explicit pkg-config path remains caller-owned in cross mode.
    explicit_path, explicit_flags, explicit_cc = run(
        'cross-explicit-path', 'x86_64-apple-darwin', 'aarch64-unknown-netbsd',
        target_pc, sysroot, str(explicit_pc))
    assert explicit_path == str(explicit_pc), explicit_path
    assert explicit_flags == f'-I{sysroot}{work}/explicit/include/explicit', explicit_flags
    assert not explicit_cc, 'sysroot cross configure queried the host linker'
    print('cross explicit PKG_CONFIG_PATH preservation PASS')

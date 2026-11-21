# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors.
"""Exercise a CMake reader, two real package replacements and their dependent wave."""

import stat
import subprocess


def archive(work, prefix, pkg, version, mode):
    stage = work / (pkg + '-stage')
    payload = stage / (pkg + '-mode')
    payload.write_text(version)
    payload.chmod(mode)
    archive = work / f'{pkg}-{version}.tgz'
    subprocess.run([prefix / 'sbin/pkg_create', '-K', work / 'real-db', '-p', stage, '-I', work / 'real-prefix',
                    '-B', stage / 'BUILD_INFO', '-c', '-mode probe', '-d', '-mode probe',
                    '-f', stage / 'PLIST', archive], check=True)
    return archive


def prepare(work, prefix, python, script, units, source):
    (work / 'real-db').mkdir()
    (work / 'real-prefix').mkdir()
    fields = ('MACHINE_ARCH', 'OPSYS', 'OS_VERSION', 'PKGTOOLS_VERSION')
    info = prefix / 'sbin/pkg_info'
    # Use the selected native bmake installation's host identity for pkg_add.
    metadata = ''.join(field + '=' + subprocess.check_output(
        [info, '-K', prefix / 'pkgdb', '-Q', field, 'bmake'], text=True) for field in fields)
    for pkg in ('short1', 'long'):
        stage = work / (pkg + '-stage')
        stage.mkdir()
        (stage / 'PLIST').write_text(pkg + '-mode\n')
        (stage / 'BUILD_INFO').write_text(f'PKGPATH=t/{pkg}\n' + metadata)
        old = archive(work, prefix, pkg, '0.9', 0o644)
        subprocess.run([prefix / 'sbin/pkg_add', '-K', work / 'real-db', old], check=True)
        assert stat.S_IMODE((work / 'real-prefix' / (pkg + '-mode')).stat().st_mode) == 0o644

    src = work / 'src'
    src.mkdir()
    for index in range(units):
        (src / f'unit{index}.c').write_text(source)
    (src / 'CMakeLists.txt').write_text(
        'cmake_minimum_required(VERSION 3.16)\nproject(probe C)\nfile(GLOB units "*.c")\n'
        'add_library(probe OBJECT ${units})\ntarget_compile_options(probe PRIVATE -O1 -ffreestanding)\n')
    subprocess.run([prefix / 'bin/cmake', '-S', src, '-B', work / 'long', '-G', 'Ninja',
                    '-DCMAKE_C_COMPILER=' + str(prefix / 'bin/clang'), '-DCMAKE_MAKE_PROGRAM=' + str(prefix / 'bin/ninja'),
                    '-DCMAKE_C_COMPILER_LAUNCHER=' + ';'.join([str(python), '-B', str(script), 'compiler'])],
                   check=True, stdout=subprocess.DEVNULL)


def build_package(work, prefix, pkg):
    new = archive(work, prefix, pkg, '1.0', 0o755)
    new.replace(work / 'bulk/packages/All' / new.name)


def replace(work, prefix, pkg):
    installed = work / 'real-prefix' / (pkg + '-mode')
    subprocess.run([prefix / 'sbin/pkg_add', '-K', work / 'real-db', '-u', work / 'bulk/packages/All' / (pkg + '-1.0.tgz')],
                   check=True)
    assert installed.read_text() == '1.0' and stat.S_IMODE(installed.stat().st_mode) == 0o755
    name = subprocess.check_output([prefix / 'sbin/pkg_info', '-K', work / 'real-db', '-e', pkg], text=True)
    assert name.splitlines() == [pkg + '-1.0']


def request_time(work):
    try:
        return (work / 'bulk/state/run/t_short1.replace').stat().st_mtime
    except FileNotFoundError:
        return None

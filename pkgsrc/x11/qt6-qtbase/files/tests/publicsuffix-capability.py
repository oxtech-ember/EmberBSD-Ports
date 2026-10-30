#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check Qt's libpsl API probe across provider changes in one CMake cache."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
for name in ('cmake', 'ninja', 'cxx', 'pkgconfig', 'network-cmake', 'new-prefix', 'old-prefix'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
for name in ('cmake', 'ninja', 'cxx', 'pkgconfig'):
    setattr(a, name, getattr(a, name).resolve(strict=True))
source = a.network_cmake.resolve(strict=True).read_text()
start = source.index('    unset(__pkg_config_checked_EmberLibPSL')
end = source.index('    qt_internal_extend_target(Network LIBRARIES', start)
block = '\n'.join(line[4:] if line.startswith('    ') else line
                  for line in source[start:end].splitlines())
with tempfile.TemporaryDirectory(prefix='qt-psl-api-') as tmp:
    root = Path(tmp); project = root / 'source'; project.mkdir()
    (project / 'CMakeLists.txt').write_text('cmake_minimum_required(VERSION 3.18)\nproject(psl_api CXX)\nfind_package(PkgConfig REQUIRED)\n' + block + '\n')
    new, old = a.new_prefix.resolve(strict=True), a.old_prefix.resolve(strict=True)
    mixed = root / 'mixed'; (mixed / 'include').mkdir(parents=True); (mixed / 'lib/pkgconfig').mkdir(parents=True)
    shutil.copy2(new / 'include/libpsl.h', mixed / 'include/libpsl.h')
    # The fixture uses the already built old provider, never a synthesized DSO.
    old_lib = next((old / 'lib').glob('libpsl.*dylib'), None) or next((old / 'lib').glob('libpsl.so*'), None)
    if old_lib is None: raise SystemExit('old libpsl library missing')
    suffix = '.dylib' if old_lib.name.endswith('.dylib') else '.so'
    shutil.copy2(old_lib.resolve(strict=True), mixed / ('lib/libpsl' + suffix))
    (mixed / 'lib/pkgconfig/libpsl.pc').write_text(f'prefix={mixed}\nlibdir=${{prefix}}/lib\nincludedir=${{prefix}}/include\nName: libpsl\nDescription: old library with new header fixture\nVersion: 0.23.3\nLibs: -L${{libdir}} -lpsl\nCflags: -I${{includedir}}\n')
    command = [str(a.cmake), '-G', 'Ninja', '-DCMAKE_MAKE_PROGRAM=' + str(a.ninja), '-DCMAKE_CXX_COMPILER=' + str(a.cxx), '-DPKG_CONFIG_EXECUTABLE=' + str(a.pkgconfig), '-DPKG_CONFIG_ARGN=--define-prefix', '-DPKG_CONFIG_USE_CMAKE_PREFIX_PATH=OFF', '-S', str(project), '-B', str(root / 'build')]
    import os
    env = os.environ.copy(); env['PKG_CONFIG_PATH'] = ''
    for name, prefix, expected in (('new', new, True), ('old', old, False), ('mixed', mixed, False), ('new-again', new, True)):
        env['PKG_CONFIG_LIBDIR'] = str(prefix / 'lib/pkgconfig') + os.pathsep + str(new / 'lib/pkgconfig')
        result = subprocess.run(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=120)
        if (result.returncode == 0) != expected or (not expected and 'Selected libpsl lacks the exact-rule API' not in result.stdout):
            raise SystemExit(name + ': unexpected result\n' + result.stdout[-3000:])
    print('PASS: new libpsl accepted; old provider and new-header/old-library rejected, restored provider accepted')

#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check native Qt layout through real metadata.
import argparse
import json
from pathlib import Path
import subprocess


def run(argv):
    result = subprocess.run([str(x) for x in argv], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f'{argv}: {result.stdout}{result.stderr}')
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('bmake', 'cmake', 'qtpaths', 'cc', 'work'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    args.work.mkdir()
    root = Path(__file__).resolve().parents[4]
    fragment = root / 'pkgsrc/x11/qt6-qtbase/host-tools.mk'
    prefix = Path(run([args.qtpaths, '--query', 'QT_INSTALL_PREFIX']))
    libexec = Path(run([args.qtpaths, '--query', 'QT_INSTALL_LIBEXECS']))
    version = run([args.qtpaths, '--qt-version'])
    assert version == '6.12.0', version
    case = args.work / 'query.mk'
    case.write_text(f'.include "{fragment}"\n')

    def reasons(host, tools=None):
        argv = [args.bmake, '-f', case, 'EMBERBSD_QT_HOST_PATH=' + str(host)]
        if tools is not None:
            argv += ['EMBERBSD_QT_HOST_LIBEXECS=' + str(tools)]
        return run(argv + ['-V', '${PKG_FAIL_REASON}'])

    assert reasons(prefix, libexec) == ''
    assert reasons(prefix, args.work / 'missing')
    assert reasons('relative', libexec)
    assert reasons(args.work / 'missing', libexec)
    legacy = args.work / 'build-tree'
    (legacy / 'libexec').mkdir(parents=True)
    metadata = legacy / 'lib/cmake/Qt6CoreTools'
    metadata.mkdir(parents=True)
    (legacy / 'libexec/moc').symlink_to(libexec / 'moc')
    (metadata / 'Qt6CoreToolsConfig.cmake').write_text('# fixture metadata\n')
    assert reasons(legacy) == ''
    (legacy / 'libexec/moc').unlink()
    assert reasons(legacy)
    (legacy / 'libexec/moc').symlink_to(libexec / 'moc')
    (metadata / 'Qt6CoreToolsConfig.cmake').unlink()
    assert reasons(legacy)
    # The previous guard rejected a valid split installation before configure.
    baseline = args.work / 'baseline.mk'
    baseline.write_text('.if !exists(${HOST}/libexec/moc)\nFAIL=yes\n.endif\n')
    if libexec != prefix / 'libexec':
        assert run([args.bmake, '-f', baseline, 'HOST=' + str(prefix), '-V', '${FAIL}']) == 'yes'
    cmake_source = args.work / 'source'
    cmake_source.mkdir()
    (cmake_source / 'CMakeLists.txt').write_text('''cmake_minimum_required(VERSION 3.25)
project(NativeQtTools C)
find_package(Qt6 6.12.0 EXACT CONFIG REQUIRED COMPONENTS CoreTools
    PATHS "${HOST_PREFIX}/lib/cmake/Qt6" NO_DEFAULT_PATH)
file(GENERATE OUTPUT "${CMAKE_BINARY_DIR}/moc-path.txt" CONTENT "$<TARGET_FILE:Qt6::moc>")
''')
    build = args.work / 'build'
    configure = [args.cmake, '-S', cmake_source, '-B', build, '-DHOST_PREFIX=' + str(prefix), '-DCMAKE_C_COMPILER=' + str(args.cc)]
    output = run(configure)
    (args.work / 'configure.log').write_text(output + '\n')
    moc = Path((build / 'moc-path.txt').read_text())
    assert moc.resolve() == (libexec / 'moc').resolve()
    assert run([moc, '--version']) == 'moc 6.12.0'
    result = {'checks': 9 + int(libexec != prefix / 'libexec'), 'version': version, 'prefix': str(prefix),
              'libexec': str(libexec), 'cmake_moc': str(moc),
              'configure': [str(x) for x in configure],
              'scope': 'native metadata and moc execution; no target build'}
    (args.work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()

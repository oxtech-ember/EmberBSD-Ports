#!/usr/bin/env python3
"""Check target metadata mapping at the buildlink root boundary."""
import pathlib
import subprocess
import sys
import tempfile

if len(sys.argv) != 3:
    raise SystemExit('usage: target-metadata-boundary.py HOST_PYTHON TARGET_METADATA_PY')
with tempfile.TemporaryDirectory(prefix='qt metadata ') as temp:
    root = pathlib.Path(temp) / 'qt'
    cmake = root / 'lib/cmake'
    cmake.mkdir(parents=True)
    qmake = root / 'mkspecs/netbsd-g++/qmake.conf'
    qmake.parent.mkdir(parents=True)
    qmake.write_text('QMAKE_MKDIR = /selected/host/bin/gmkdir -p\n')
    sample = cmake / 'check.cmake'
    work = pathlib.Path(temp) / 'work'
    sysroot = pathlib.Path(temp) / 'sysroot'
    host_tools = pathlib.Path(temp) / 'host-tools'
    command = [sys.argv[1], '-B', sys.argv[2], str(root), str(sysroot), str(work),
               '/usr/pkg', str(host_tools), '/usr/pkg/bin/clang',
               '/usr/pkg/bin/clang++', '--module']
    sample.write_text(f'set(ROOT "{work}/.buildlink")\nset(CHILD "{work}/.buildlink/lib")\n'
                      'QMAKE_CC = /old/compiler\nQMAKE_CXX = /old/compiler++\n')
    subprocess.run(command, check=True)
    assert sample.read_text() == ('set(ROOT "/usr/pkg")\nset(CHILD "/usr/pkg/lib")\n'
                                  'QMAKE_CC = /usr/pkg/bin/clang\n'
                                  'QMAKE_CXX = /usr/pkg/bin/clang++\n')
    assert qmake.read_text() == 'QMAKE_MKDIR = mkdir -p\n'
    sample.write_text(f'set(BAD "{work}/.buildlink-other")\n')
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode != 0 and 'unresolved build path' in result.stderr
    sample.unlink()
    sbom = root / 'sbom' / 'qtbase.spdx'
    sbom.parent.mkdir(parents=True)
    sbom.write_text(
        'SPDXVersion: SPDX-2.3\n'
        'PackageName: qtbase\n'
        'PackageDownloadLocation: https://example.invalid/qtbase.tar.xz\n'
        'LicenseConcluded: NOASSERTION\n'
        'qtbase was configured with:\n'
        f'    qt6/configure -DROOT={work}/.buildlink/lib;{work}/.buildlink/include/python3.15 '
        f'-DCMAKE_FIND_ROOT_PATH={work}/.buildlink;{sysroot} '
        f'-DHostPrefix={host_tools} '
        f'-DPython_EXECUTABLE={host_tools}/bin/python3.15 '
        f'-DSimilarPrefix={host_tools}-extra/bin/tool -DCMAKE_SYSROOT={sysroot}\n'
        '</text>\n'
    )
    external = pathlib.Path(temp) / 'external.spdx'
    external.write_text(f'Unowned: {work}/.buildlink\n')
    symlink = sbom.parent / 'linked.spdx'
    symlink.symlink_to(external)
    subprocess.run(command, check=True)
    assert sbom.read_text() == (
        'SPDXVersion: SPDX-2.3\n'
        'PackageName: qtbase\n'
        'PackageDownloadLocation: https://example.invalid/qtbase.tar.xz\n'
        'LicenseConcluded: NOASSERTION\n'
        'qtbase was configured with:\n'
        '    qt6/configure -DROOT=/usr/pkg/lib;/usr/pkg/include/python3.15 '
        f'-DCMAKE_FIND_ROOT_PATH=/usr/pkg;{sysroot} '
        '-DHostPrefix=${SDK_NATIVE_PREFIX} '
        '-DPython_EXECUTABLE=${SDK_NATIVE_PREFIX}/bin/python3.15 '
        f'-DSimilarPrefix={host_tools}-extra/bin/tool -DCMAKE_SYSROOT={sysroot}\n'
        '</text>\n'
    )
    assert f'{host_tools}/' not in sbom.read_text()
    assert f'{host_tools}-extra/bin/tool' in sbom.read_text()
    assert str(sysroot) in sbom.read_text()
    assert symlink.is_symlink() and external.read_text() == f'Unowned: {work}/.buildlink\n'
    sbom.write_text(
        'SPDXVersion: SPDX-2.3\n'
        'PackageName: qtsvg\n'
        'PackageDownloadLocation: https://example.invalid/qtsvg.tar.xz\n'
        'LicenseConcluded: NOASSERTION\n'
        'qtsvg was configured with:\n'
        f'    cmake -DHostPrefix={host_tools} -DPython={host_tools}/bin/python3.15 '
        f'-DSimilarPrefix={host_tools}-extra/bin/tool\n'
        '</text>\n'
    )
    subprocess.run(command, check=True)
    assert sbom.read_text() == (
        'SPDXVersion: SPDX-2.3\n'
        'PackageName: qtsvg\n'
        'PackageDownloadLocation: https://example.invalid/qtsvg.tar.xz\n'
        'LicenseConcluded: NOASSERTION\n'
        'qtsvg was configured with:\n'
        '    cmake -DHostPrefix=${SDK_NATIVE_PREFIX} '
        '-DPython=${SDK_NATIVE_PREFIX}/bin/python3.15 '
        f'-DSimilarPrefix={host_tools}-extra/bin/tool\n'
        '</text>\n'
    )
print('PASS: target metadata buildlink and native-prefix boundaries')

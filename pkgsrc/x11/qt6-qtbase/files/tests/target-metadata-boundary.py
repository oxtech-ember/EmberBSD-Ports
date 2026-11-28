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
    tools = pathlib.Path(temp) / 'target-tools'
    alias = pathlib.Path(temp) / 'sysroot-alias'
    sysroot.mkdir()
    alias.symlink_to(sysroot, target_is_directory=True)
    command = [sys.argv[1], '-B', sys.argv[2], str(root), str(alias), str(work),
               '/usr/pkg', str(host_tools), '/usr/pkg/bin/clang',
               '/usr/pkg/bin/clang++', str(tools), '--module']
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
        f'-DCMAKE_AR:FILEPATH={tools}/bin/aarch64--netbsd-ar '
        f'-DCMAKE_RANLIB:FILEPATH={tools}/bin/aarch64--netbsd-ranlib '
        f'-DCMAKE_LIBRARY_PATH:STRING={alias}/usr/pkg/llvm/lib '
        f'-DHostPrefix={host_tools} '
        f'-DPython_EXECUTABLE={host_tools}/bin/python3.15 '
        f'-DSimilarPrefix={host_tools}-extra/bin/tool -DNeighbor={tools}-extra/bin/ar '
        f'-DPHYSICAL={sysroot.resolve()} -DCMAKE_SYSROOT={sysroot}\n'
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
        '-DCMAKE_FIND_ROOT_PATH=/usr/pkg;${SDK_TARGET_SYSROOT} '
        '-DCMAKE_AR:FILEPATH=${SDK_TARGET_TOOLDIR}/bin/aarch64--netbsd-ar '
        '-DCMAKE_RANLIB:FILEPATH=${SDK_TARGET_TOOLDIR}/bin/aarch64--netbsd-ranlib '
        '-DCMAKE_LIBRARY_PATH:STRING=${SDK_TARGET_SYSROOT}/usr/pkg/llvm/lib '
        '-DHostPrefix=${SDK_NATIVE_PREFIX} '
        '-DPython_EXECUTABLE=${SDK_NATIVE_PREFIX}/bin/python3.15 '
        f'-DSimilarPrefix={host_tools}-extra/bin/tool -DNeighbor={tools}-extra/bin/ar '
        '-DPHYSICAL=${SDK_TARGET_SYSROOT} -DCMAKE_SYSROOT=${SDK_TARGET_SYSROOT}\n'
        '</text>\n'
    )
    assert f'{host_tools}/' not in sbom.read_text()
    assert f'{host_tools}-extra/bin/tool' in sbom.read_text()
    assert str(sysroot) not in sbom.read_text()
    assert str(alias) not in sbom.read_text()
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
    comment = ('PackageComment: <text>\nCMake target name: WaylandCompositor_Attribution_xml\n'
               '    Information extracted from:\n     {}\n    Entry index: 0\n</text>\n')
    source = '/usr/pkg/qt6/share/qt6/wayland/protocols/example/qt_attribution.json'
    sibling = f'{alias}-other{source}'
    license_text = (f'ExtractedText: <text>\n    Information extracted from:\n'
                    f'     {sysroot.resolve()}{source}\n</text>\n')
    paths = [f'{alias}{source}', f'{sysroot.resolve()}{source}', sibling, f'/src_dir{source}']
    sbom.write_text(''.join(comment.format(p) for p in paths) + license_text)
    subprocess.run(command, check=True)
    expected = [f'/sysroot_dir{source}', f'/sysroot_dir{source}', *paths[2:]]
    assert sbom.read_text() == ''.join(comment.format(p) for p in expected) + license_text
    catalog_root = pathlib.Path(temp) / 'translations-only'
    catalogs = catalog_root / 'translations'
    catalogs.mkdir(parents=True)
    (catalogs / 'qtbase_ru.qm').write_bytes(b'catalog')
    catalog_sbom = catalog_root / 'sbom/qttranslations.spdx'
    catalog_sbom.parent.mkdir()
    catalog_sbom.write_text('qttranslations was configured with:\n'
                            f' -DROOT={work}/.buildlink/lib -DTOOLS={host_tools}/bin\n'
                            '</text>\n')
    data_command = command.copy()
    data_command[3] = str(catalog_root)
    data_command[-1] = '--translations'
    subprocess.run(data_command, check=True)
    assert catalog_sbom.read_text() == ('qttranslations was configured with:\n'
                                        ' -DROOT=/usr/pkg/lib -DTOOLS=${SDK_NATIVE_PREFIX}/bin\n'
                                        '</text>\n')
    data_command[-1] = '--module'
    failed = subprocess.run(data_command, capture_output=True, text=True)
    assert failed.returncode != 0 and 'not a staged Qt module tree' in failed.stderr
    data_command[-1] = '--translations'
    (catalogs / 'qtbase_ru.qm').unlink()
    failed = subprocess.run(data_command, capture_output=True, text=True)
    assert failed.returncode != 0 and 'not a staged Qt translations tree' in failed.stderr
print('PASS: target metadata buildlink and native-prefix boundaries')

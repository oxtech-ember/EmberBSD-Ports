#!/usr/bin/env python3
"""Check target metadata mapping at the buildlink root boundary."""
import pathlib
import subprocess
import sys
import tempfile

if len(sys.argv) != 3:
    raise SystemExit('usage: target-metadata-boundary.py PERL TARGET_METADATA_PL')
with tempfile.TemporaryDirectory(prefix='qt metadata ') as temp:
    root = pathlib.Path(temp) / 'qt'
    cmake = root / 'lib/cmake'
    cmake.mkdir(parents=True)
    sample = cmake / 'check.cmake'
    work = pathlib.Path(temp) / 'work'
    command = [sys.argv[1], sys.argv[2], str(root), str(pathlib.Path(temp) / 'sysroot'), str(work), '/usr/pkg', '--module']
    sample.write_text(f'set(ROOT "{work}/.buildlink")\nset(CHILD "{work}/.buildlink/lib")\n')
    subprocess.run(command, check=True)
    assert sample.read_text() == 'set(ROOT "/usr/pkg")\nset(CHILD "/usr/pkg/lib")\n'
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
        f'    qt6/configure -DROOT={work}/.buildlink/lib;{work}/.buildlink/include/python3.15\n'
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
        '    qt6/configure -DROOT=/usr/pkg/lib;/usr/pkg/include/python3.15\n'
        '</text>\n'
    )
    assert symlink.is_symlink() and external.read_text() == f'Unowned: {work}/.buildlink\n'
print('PASS: target metadata buildlink boundary')

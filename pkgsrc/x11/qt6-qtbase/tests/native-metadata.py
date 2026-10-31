#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check the native installed Qt metadata rewrite."""
from pathlib import Path
import subprocess
import tempfile

script = Path(__file__).resolve().parents[1] / 'files' / 'target-metadata.pl'
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    cmake = root / 'lib/cmake/Qt6/qt.toolchain.cmake'
    extra = root / 'lib/cmake/Qt6BuildInternals/QtBuildInternalsExtra.cmake'
    cmake.parent.mkdir(parents=True)
    extra.parent.mkdir(parents=True)
    cmake.write_text('set(__qt_initial_c_compiler "/work/cc")\n'
                     'set(__qt_initial_cxx_compiler "/work/cxx")\n')
    extra.write_text('set(QT_SOURCE_TREE "/work/qtbase" CACHE PATH "" FORCE)\n')
    subprocess.run(['perl', str(script), '--native', str(root),
                    '/selected/bin/clang', '/selected/bin/clang++'], check=True)
    assert '"/selected/bin/clang"' in cmake.read_text()
    assert '"/selected/bin/clang++"' in cmake.read_text()
    assert 'set(QT_SOURCE_TREE ""' in extra.read_text()
    strange = '/selected/quote"back\\dollar$/clang'
    for _ in range(2):
        subprocess.run(['perl', str(script), '--native', str(root), strange,
                        '/selected/bin/clang++'], check=True)
    assert '/selected/quote\\"back\\\\dollar\\$/clang' in cmake.read_text()
    cmake.write_text('missing expected compiler fields\n')
    result = subprocess.run(['perl', str(script), '--native', str(root),
                             '/selected/bin/clang', '/selected/bin/clang++'],
                            capture_output=True)
    assert result.returncode != 0
    # The pre-existing target mode retains target compiler selection and
    # discards build-host source metadata independently of the native mode.
    (root / 'bin').mkdir()
    (root / 'bin/qmake').touch()
    (root / 'lib/cmake/Qt6/Qt6Config.cmake').touch()
    cmake.write_text('set(__qt_initial_c_compiler "/target/bin/cc")\n')
    extra.write_text('set(QT_SOURCE_TREE "/work/qtbase" CACHE PATH "" FORCE)\n')
    subprocess.run(['perl', str(script), str(root), '/target/sysroot',
                    '/target/work', '/usr/pkg'], check=True)
    assert '"/target/bin/cc"' in cmake.read_text()
    assert 'set(QT_SOURCE_TREE ""' in extra.read_text()
print('PASS: native metadata selects compilers, clears source and rejects malformed input')

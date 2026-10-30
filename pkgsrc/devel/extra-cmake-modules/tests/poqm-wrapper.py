#!/usr/bin/env python3
"""Exercise the installed ECM PO/QM module with and without a Qt tool wrapper."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

p = argparse.ArgumentParser()
for name in ('cmake', 'ninja', 'cxx', 'qt', 'module', 'patch', 'gpatch', 'python', 'launcher', 'view', 'sdk'):
    p.add_argument('--' + name, required=True, type=Path)
p.add_argument("--deployment", required=True)
a = p.parse_args()
for name, value in vars(a).items():
    if name == "deployment":
        continue
    if not value.is_absolute() or not value.exists():
        p.error(f'{name} must be an existing absolute path')
with tempfile.TemporaryDirectory(prefix='ecm wrapper ') as td:
    root = Path(td)
    shutil.copy2(a.module / 'ECMPoQmTools.cmake', root)
    shutil.copy2(a.module / 'QtVersionOption.cmake', root)
    subprocess.run([str(a.gpatch), '-d', str(root), '-p1', '-F0', '-i', str(a.patch)], check=True)
    (root / 'CMakeLists.txt').write_text('''cmake_minimum_required(VERSION 3.21)
project(ECMPoQmWrapper LANGUAGES CXX)
set(QT_MAJOR_VERSION 6)
find_package(Qt6 REQUIRED COMPONENTS LinguistTools)
include("${CMAKE_CURRENT_SOURCE_DIR}/ECMPoQmTools.cmake")
ecm_process_po_files_as_qm(de ALL PO_FILES "${CMAKE_CURRENT_SOURCE_DIR}/input.po")
''')
    (root / 'input.po').write_text('''msgid ""
msgstr "Content-Type: text/plain; charset=UTF-8\\n"

msgid "Hello"
msgstr "Hallo"
''')
    wrapper = root / 'tool wrapper.sh'
    wrapper.write_text('''#!/bin/sh
printf '%s\\n' "$1" >> "$ECM_WRAPPER_LOG"
exec "$QT_PYTHON" -I -S "$QT_LAUNCHER" --runtime-view "$QT_VIEW" -- "$@"
''')
    wrapper.chmod(0o755)
    env = dict(os.environ, ECM_WRAPPER_LOG=str(root / 'wrapper.log'), QT_PYTHON=str(a.python), QT_LAUNCHER=str(a.launcher), QT_VIEW=str(a.view))
    prefix = [str(a.python), '-I', '-S', str(a.launcher), '--runtime-view', str(a.view), '--']
    for mode in ('direct', 'wrapped'):
        build = root / ('build ' + mode)
        cmd = [str(a.cmake), '-S', str(root), '-B', str(build), '-G', 'Ninja',
               '-DCMAKE_MAKE_PROGRAM=' + str(a.ninja), '-DCMAKE_PREFIX_PATH=' + str(a.qt),
               '-DCMAKE_CXX_COMPILER=' + str(a.cxx), '-DCMAKE_OSX_SYSROOT=' + str(a.sdk),
               '-DCMAKE_OSX_DEPLOYMENT_TARGET=' + a.deployment, '-DQT_TOOL_COMMAND_WRAPPER_PATH=' + (str(wrapper) if mode == 'wrapped' else '')]
        subprocess.run(prefix + cmd, env=env, check=True)
        subprocess.run(prefix + [str(a.cmake), '--build', str(build)], env=env, check=True)
        qm = build / 'ECMPoQm/de/input.qm'
        if not qm.is_file() or not qm.stat().st_size:
            raise RuntimeError('missing QM output: ' + str(qm))
    calls = (root / 'wrapper.log').read_text().splitlines()
    if len(calls) != 2 or not calls[0].endswith('/lconvert') or not calls[1].endswith('/lrelease'):
        raise RuntimeError('unexpected wrapper calls: ' + repr(calls))
print('ECM direct and wrapped PO to QM PASS')

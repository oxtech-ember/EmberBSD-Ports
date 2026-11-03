#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check minimal Qt Declarative producer and consumer metadata against pkgsrc."""
import argparse
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--pkgsrc', type=Path, required=True)
p.add_argument('--archive', type=Path, required=True)
p.add_argument('--bmake', type=Path, required=True)
p.add_argument('--makeconf', type=Path, required=True)
p.add_argument('--work-parent', type=Path, required=True)
a = p.parse_args()
root = Path(__file__).resolve().parents[3]
recipe = root/'pkgsrc/lang/qt6-qtdeclarative'
digest = re.search(r'^SHA512 \(' + re.escape(a.archive.name) + r'\) = ([a-f0-9]+)$',
                   (recipe/'distinfo').read_text(), re.M)
if not digest or hashlib.sha512(a.archive.read_bytes()).hexdigest() != digest.group(1):
    raise SystemExit('wrong Qt Declarative distfile')
with tarfile.open(a.archive) as tar:
    cmake = tar.extractfile('qtdeclarative-everywhere-src-6.12.0/CMakeLists.txt').read().decode()
    src = tar.extractfile('qtdeclarative-everywhere-src-6.12.0/src/CMakeLists.txt').read().decode()
if 'OPTIONAL_COMPONENTS Gui Network Widgets OpenGL OpenGLWidgets Sql Concurrent Test TestInternalsPrivate LanguageServerPrivate Svg' not in cmake:
    raise SystemExit('upstream optional component contract changed')
if 'AND TARGET Qt::LanguageServerPrivate' not in src or 'add_subdirectory(qmlls)' not in src:
    raise SystemExit('upstream qmlls target guard changed')
plist = (recipe/'PLIST').read_text().splitlines()
marker = '${PLIST.languageserver}'
if sum(x.startswith(marker) for x in plist) != 67 or 'qt6/lib/cmake/Qt6Qml/Qt6UpdateQmllsIni.cmake' not in plist:
    raise SystemExit('QmlLS-only PLIST guard is incomplete')
with tempfile.TemporaryDirectory(prefix='qtqml-options-', dir=a.work_parent) as work:
    w = Path(work)
    for entry in a.pkgsrc.iterdir():
        if entry.name not in ('lang', 'meta-pkgs'):
            (w/entry.name).symlink_to(entry, target_is_directory=entry.is_dir())
    for category, excluded in (('lang', {'qt6-qtdeclarative'}), ('meta-pkgs', set())):
        (w/category).mkdir()
        for entry in (a.pkgsrc/category).iterdir():
            if entry.name not in excluded:
                (w/category/entry.name).symlink_to(entry, target_is_directory=entry.is_dir())
    shutil.copytree(recipe, w/'lang/qt6-qtdeclarative', symlinks=True)
    consumer = w/'meta-pkgs/qml-consumer'
    consumer.mkdir()
    (consumer/'Makefile').write_text('DISTNAME= qml-consumer-check-1\nCATEGORIES= meta-pkgs\n'
        'COMMENT= Qt Declarative metadata consumer\nLICENSE= 2-clause-bsd\n'
        '.include "../../lang/qt6-qtdeclarative/buildlink3.mk"\n.include "../../mk/bsd.pkg.mk"\n')
    env = os.environ.copy()
    env['MAKECONF'] = str(a.makeconf)
    for selection, minimal in (('', False), ('minimal-runtime', True)):
        r = subprocess.run([str(a.bmake), '-C', str(w/'lang/qt6-qtdeclarative'),
                            'PKG_OPTIONS.qt6-qtdeclarative='+selection, 'show-vars',
                            'VARNAMES=PKG_OPTIONS PLIST.languageserver CMAKE_CONFIGURE_ARGS BUILDLINK_TREE'],
                           env=env, text=True, capture_output=True, check=True)
        lines = r.stdout.splitlines()
        if len(lines) != 4:
            raise SystemExit('unexpected producer metadata output')
        options, plist, flags, graph = lines
        if ('minimal-runtime' in options.split()) != minimal or (plist.strip() == 'yes') == minimal:
            raise SystemExit('producer selection/PLIST mismatch')
        if ('-DCMAKE_DISABLE_FIND_PACKAGE_Qt6LanguageServerPrivate=TRUE' in flags.split()) != minimal:
            raise SystemExit('LanguageServerPrivate find guard mismatch')
        for name in ('qt6-qtimageformats', 'qt6-qtlanguageserver'):
            if (name in graph.split()) == minimal:
                raise SystemExit('producer dependency mismatch: '+name)
        r = subprocess.run([str(a.bmake), '-C', str(consumer),
                            'PKG_BUILD_OPTIONS.qt6-qtdeclarative='+selection, 'show-var',
                            'VARNAME=BUILDLINK_TREE'], env=env, text=True, capture_output=True, check=True)
        graph = r.stdout.split()
        for name in ('qt6-qtimageformats', 'qt6-qtlanguageserver'):
            if (name in graph) == minimal:
                raise SystemExit('consumer dependency mismatch: '+name)
        if not {'qt6-qtbase', 'qt6-qtsvg', 'qt6-qtshadertools'} <= set(graph):
            raise SystemExit('required Qt consumer libraries disappeared')
    r = subprocess.run([str(a.bmake), '-C', str(w/'lang/qt6-qtdeclarative'),
                        'USE_CROSS_COMPILE=no', 'PKG_OPTIONS.qt6-qtdeclarative=minimal-runtime',
                        'show-var', 'VARNAME=PKG_FAIL_REASON'], env=env, text=True, capture_output=True)
    if r.returncode or 'not supported' not in r.stdout:
        raise SystemExit('native minimal-runtime was not rejected')
print('PASS: Qt Declarative default/minimal producer and consumer dependency graphs')

#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Real OBJ import; executable presence is insufficient.
set -eu
[ "$#" = 2 ] || { echo 'Usage: check-quick3d-host.sh HOST_QT NEW_WORK' >&2; exit 2; }
qt=$1
[ "$("$qt/bin/qmake" -query QT_VERSION)" = 6.12.0 ]
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
cat > "$work/triangle.obj" <<'OBJ'
o EmberTriangle
v 0 0 0
v 1 0 0
v 0 1 0
f 1 2 3
OBJ
QT_QPA_PLATFORM=minimal "$qt/bin/balsam" -o "$work" "$work/triangle.obj" > "$work/import.log" 2>&1
[ -s "$work/Triangle.qml" ]
[ -s "$work/meshes/emberTriangle_mesh.mesh" ]
grep 'emberTriangle_mesh.mesh' "$work/Triangle.qml" >/dev/null
"$qt/libexec/qmlcachegen" --only-bytecode --resource-path /Triangle.qml \
    -o "$work/triangle-cache.cpp" "$work/Triangle.qml" > "$work/qml.log" 2>&1
[ -s "$work/triangle-cache.cpp" ]
mkdir "$work/negative"
# Upstream balsam may return success for import errors: inspect output too.
QT_QPA_PLATFORM=minimal "$qt/bin/balsam" -o "$work/negative" "$work/missing.obj" > "$work/missing.log" 2>&1 || :
[ -z "$(ls -A "$work/negative")" ]
grep -i 'error\|fail\|not.*exist' "$work/missing.log" >/dev/null
shasum -a 256 "$work/triangle.obj" "$work/Triangle.qml" "$work/meshes/emberTriangle_mesh.mesh" "$work/triangle-cache.cpp" > "$work/outputs.sha256"
echo 'PASS: native Quick3D OBJ import, mesh output, generated QML bytecode and missing-input check'

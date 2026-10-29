#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Usage: run.sh QTBASE PYTHON SDK_SOURCE RUNTIME_VIEW
set -eu
[ "$#" = 4 ] || { echo 'usage: run.sh QTBASE PYTHON SDK_SOURCE RUNTIME_VIEW' >&2; exit 2; }
qt=$1 python=$2 sdk=$3 view=$4
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
out=$(mktemp -d "${TMPDIR:-/tmp}/ember-balsam.XXXXXXXX")
trap 'rm -rf "$out"' EXIT HUP INT TERM
QT_QPA_PLATFORM=minimal DYLD_FRAMEWORK_PATH="$qt/lib" \
    "$python" -I "$sdk/scripts/run-darwin-with-runtime.py" --runtime-view "$view" -- \
    "$qt/bin/balsam" -o "$out" "$here/triangle.gltf"
test -s "$out/Triangle.qml"
test -s "$out/meshes/meshes_0__mesh.mesh"
echo 'PASS: Balsam imports a triangle and writes QML and mesh'

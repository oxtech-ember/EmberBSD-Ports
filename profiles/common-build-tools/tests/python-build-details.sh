#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), target metadata under a different host version.
set -eu
[ "$#" = 4 ] || { echo "Usage: $0 PYTHON_SOURCE PYTHON_BUILD HOST_PYTHON NEW_WORK" >&2; exit 2; }
source=$1 build=$2 python=$3 work=$4
arch=${EMBERBSD_CROSS_ARCH:-aarch64}
case "$arch" in
    aarch64) machine=evbarm;;
    x86_64) machine=amd64;;
    *) echo "Unsupported CPU: $arch" >&2; exit 2;;
esac
major=$(awk '$2 == "PY_MAJOR_VERSION" {print $3}' "$source/Include/patchlevel.h")
minor=$(awk '$2 == "PY_MINOR_VERSION" {print $3}' "$source/Include/patchlevel.h")
mkdir "$work"
mkdir -p "$work/Tools/build" "$work/Include"
cp "$source/Tools/build/generate-build-details.py" "$work/Tools/build/"
# A synthetic source-header micro version differs from any real interpreter.
# Only source metadata is changed; no synthetic Python executable is involved.
sed 's/^#define PY_MICRO_VERSION .*/#define PY_MICRO_VERSION 199/' \
    "$source/Include/patchlevel.h" > "$work/Include/patchlevel.h"
configdir=$build/$(cat "$build/pybuilddir.txt")
_PYTHON_HOST_PLATFORM=netbsd-$arch \
    PYTHON_BUILD_DETAILS_PLATFORM=netbsd-11.0-$machine \
    _PYTHON_PROJECT_BASE="$build" PYTHONPATH="$source/Lib" \
    _PYTHON_SYSCONFIGDATA_NAME=_sysconfigdata_netbsd11 \
    _PYTHON_SYSCONFIGDATA_PATH="$configdir" \
    "$python" "$work/Tools/build/generate-build-details.py" "$work/details.json"
awk '/"micro":/ { if ($2 != "199,") exit 1; count++ }
    END { if (count != 2) exit 1 }' "$work/details.json"
grep -Fq "\"platform\": \"netbsd-11.0-$machine\"" "$work/details.json"
grep -Fq "\".cpython-$major$minor.so\"" "$work/details.json"
grep -Fq "/config-$major.$minor/libpython$major.$minor.a" "$work/details.json"
if grep -q darwin "$work/details.json"; then
    echo 'Host platform leaked into build details' >&2; exit 1
fi
echo 'PASS: target source version, runtime platform, loader suffixes and static-library path'

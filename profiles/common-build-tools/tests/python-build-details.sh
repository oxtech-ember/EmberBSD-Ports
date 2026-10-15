#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), target metadata under a different host version.
set -eu
[ "$#" = 4 ] || { echo "Usage: $0 PYTHON_SOURCE PYTHON_BUILD HOST_PYTHON NEW_WORK" >&2; exit 2; }
source=$1 build=$2 python=$3 work=$4
mkdir "$work"
mkdir -p "$work/Tools/build" "$work/Include"
cp "$source/Tools/build/generate-build-details.py" "$work/Tools/build/"
# A synthetic source-header micro version differs from any real interpreter.
# Only source metadata is changed; no synthetic Python executable is involved.
sed 's/^#define PY_MICRO_VERSION .*/#define PY_MICRO_VERSION 199/' \
    "$source/Include/patchlevel.h" > "$work/Include/patchlevel.h"
configdir=$build/$(cat "$build/pybuilddir.txt")
_PYTHON_HOST_PLATFORM=netbsd-aarch64 \
    PYTHON_BUILD_DETAILS_PLATFORM=netbsd-11.0-evbarm \
    _PYTHON_PROJECT_BASE="$build" PYTHONPATH="$source/Lib" \
    _PYTHON_SYSCONFIGDATA_NAME=_sysconfigdata_netbsd11 \
    _PYTHON_SYSCONFIGDATA_PATH="$configdir" \
    "$python" "$work/Tools/build/generate-build-details.py" "$work/details.json"
awk '/"micro":/ { if ($2 != "199,") exit 1; count++ }
    END { if (count != 2) exit 1 }' "$work/details.json"
grep -q '"platform": "netbsd-11.0-evbarm"' "$work/details.json"
grep -q '".cpython-314.so"' "$work/details.json"
grep -q '/config-3.15/libpython3.15.a' "$work/details.json"
if grep -q darwin "$work/details.json"; then
    echo 'Host platform leaked into build details' >&2; exit 1
fi
echo 'PASS: target source version, runtime platform, loader suffixes and static-library path'

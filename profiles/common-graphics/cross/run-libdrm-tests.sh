#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; run upstream libdrm tests on the actual target.
set -eu
[ "$(uname -s)" = NetBSD ] && [ "$(uname -p)" = aarch64 ] || {
    echo 'Run on EmberBSD/NetBSD AArch64' >&2; exit 2
}
cd -- "$(dirname -- "$0")"
test_dir=$(pwd -P)
export LD_LIBRARY_PATH=$test_dir
unset LD_PRELOAD
uname -a
expected=$(realpath "$test_dir/libdrm.so.2.134.0")
# Check every loader resolution before executing any test. A missing SONAME
# link can otherwise fall back to an installed system libdrm.
for program in hash drmsl drmdevice; do
    ldd "./$program" > "$program.ldd"
    cat "$program.ldd"
    loaded=$(awk '$1 == "-ldrm.2" && $2 == "=>" { path = $3; count++ }
        END { if (count != 1) exit 1; print path }' "$program.ldd") || {
        echo "Cannot identify libdrm for $program" >&2; exit 1
    }
    case "$loaded" in /*) ;; *) echo "Unresolved libdrm for $program" >&2; exit 1;; esac
    [ "$(realpath "$loaded")" = "$expected" ] || {
        echo "Foreign libdrm selected for $program: $loaded" >&2; exit 1
    }
done
./hash > hash.log 2>&1
echo 'PASS: hash'
./drmsl > drmsl.log 2>&1
echo 'PASS: drmsl'
# This upstream inspection script can use an existing target interpreter.
# It is a test tool, not a libdrm runtime dependency.
"${PYTHON:-python3.15}" ./symbols-check.py --lib ./libdrm.so.2.134.0 \
    --symbols-file ./core-symbols.txt --nm "${NM:-nm}"
echo 'PASS: core-symbols-check'
if ./drmdevice > drmdevice.log 2>&1; then
    echo 'PASS: drmdevice enumeration (not rendering)'
else
    status=$?
    cat drmdevice.log
    [ "$status" -eq 77 ] || exit "$status"
    echo 'SKIP: drmdevice found no DRM device; hardware acceptance pending'
fi

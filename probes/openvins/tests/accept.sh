#!/bin/sh
# SPDX-License-Identifier: MIT
# Target-side acceptance of a cross-built probe. Run on the EmberBSD device:
# it needs only base tools and the accepted GCC16 runtime, no build tools.
# Usage: sh accept.sh ABS_ACCEPT_DIR
set -eu
[ "$#" = 1 ] || { echo 'Usage: accept.sh ABS_ACCEPT_DIR' >&2; exit 2; }
dir=$1
case "$dir" in /*) ;; *) echo 'Use an absolute accept directory.' >&2; exit 2 ;; esac
[ -x "$dir/openvins-contract" ] && [ -d "$dir/lib" ] || {
    echo 'The staged accept directory is missing the consumer or libraries.' >&2; exit 2;
}
LD_LIBRARY_PATH=$dir/lib:/usr/pkg/gcc16/lib
export LD_LIBRARY_PATH
ldd "$dir/openvins-contract" > "$dir/installed-linkage.txt"
if grep -E 'not found|libc[+][+]' "$dir/installed-linkage.txt" >/dev/null; then
    echo 'Missing dependency or mixed C++ runtime on the target.' >&2; exit 1;
fi
expected_runtime=$(/usr/pkg/gcc16/bin/g++ -print-file-name=libstdc++.so)
[ -f "$expected_runtime" ] || { echo 'The target GCC16 runtime is missing.' >&2; exit 1; }
expected_runtime=$(realpath "$expected_runtime")
loaded_runtime=$(awk '/libstdc[+][+]/ {print $3}' "$dir/installed-linkage.txt")
[ -n "$loaded_runtime" ] && [ "$(printf '%s\n' "$loaded_runtime" | wc -l | tr -d ' ')" = 1 ] || {
    echo 'Expected exactly one loaded C++ runtime.' >&2; exit 1;
}
[ "$(realpath "$loaded_runtime")" = "$expected_runtime" ] || {
    echo 'Loaded C++ runtime differs from the target GCC16 runtime.' >&2; exit 1;
}
echo 'PASS installed library and coherent C++ runtime linkage'
"$dir/openvins-contract"

#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Real package and numerical consumer checks.
set -eu
[ "$#" = 4 ] || { echo 'Usage: run-target.sh PACKAGE CONTRACT UPSTREAM_TEST NEW_OUTPUT' >&2; exit 2; }
package=$1 contract=$2 upstream=$3 out=$4
[ "$(uname -s)" = NetBSD ] && [ "$(uname -p)" = aarch64 ]
for path do case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2;; esac; done
[ ! -e "$out" ] && [ ! -L "$out" ]
[ -z "${LD_LIBRARY_PATH:-}${LD_PRELOAD:-}" ]
PATH=/usr/pkg/bin:/bin:/usr/bin:/sbin:/usr/sbin; export PATH
LC_ALL=C; export LC_ALL
mkdir "$out"
uname -a > "$out/platform.txt"
pkg_add "$package"
pkg_info -e ruckig-0.19.4
pkg_admin check ruckig > "$out/integrity.txt"
ldd "$contract" > "$out/linkage.txt"
grep -q '/usr/pkg/lib/libruckig.so' "$out/linkage.txt"
grep -q '/usr/pkg/gcc16/lib/libstdc++.so.7' "$out/linkage.txt"
if grep -q 'not found' "$out/linkage.txt"; then exit 1; fi
for mode in analytic online invalid; do
    "$contract" "$mode" > "$out/$mode.log" 2>&1
    cat "$out/$mode.log"
done
"$upstream" 1000 42 > "$out/upstream.log" 2>&1
grep -q 'Status: SUCCESS' "$out/upstream.log"
pkg_delete ruckig-0.19.4
[ ! -e /usr/pkg/lib/libruckig.so ]
if pkg_info -e ruckig-0.19.4; then echo 'Package remained registered.' >&2; exit 1; fi
if "$contract" analytic > "$out/removed.log" 2>&1; then
    echo 'Removed library remained usable.' >&2; exit 1
fi
pkg_add "$package"
pkg_admin check ruckig > "$out/reinstalled-integrity.txt"
"$contract" analytic > "$out/reinstalled.log" 2>&1
echo 'PASS: installed Ruckig numerical contracts, upstream tests, removal and reinstallation'

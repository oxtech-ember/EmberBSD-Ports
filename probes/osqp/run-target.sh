#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Installed solver and package-cycle checks.
set -eu
[ "$#" = 5 ] || { echo 'Usage: run-target.sh PACKAGE CONTRACT INTERRUPT_TEST DERIVATIVE_TEST NEW_OUTPUT' >&2; exit 2; }
package=$1 contract=$2 interrupt=$3 derivative=$4 out=$5
[ "$(uname -s)" = NetBSD ] && [ "$(uname -p)" = aarch64 ] || exit 1
for path do case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2;; esac; done
[ ! -e "$out" ] && [ ! -L "$out" ] || { echo 'Output path already exists.' >&2; exit 2; }
[ -z "${LD_LIBRARY_PATH:-}${LD_PRELOAD:-}" ]
PATH=/usr/pkg/bin:/bin:/usr/bin:/sbin:/usr/sbin; export PATH
LC_ALL=C; export LC_ALL
mkdir "$out"
uname -a > "$out/platform.txt"
pkg_add "$package"
pkg_info -e osqp-1.0.0
pkg_admin check osqp > "$out/integrity.txt"
ldd "$contract" "$interrupt" "$derivative" > "$out/linkage.txt"
grep -q '/usr/pkg/lib/libosqp.so' "$out/linkage.txt"
if grep -q 'not found' "$out/linkage.txt"; then exit 1; fi
grep -q '^#define OSQP_ENABLE_DERIVATIVES' /usr/pkg/include/osqp/osqp_configure.h
for mode in qp infeasible; do
    "$contract" "$mode" > "$out/$mode.log" 2>&1
    cat "$out/$mode.log"
done
"$interrupt" > "$out/interrupt.log" 2>&1
cat "$out/interrupt.log"
"$derivative" > "$out/derivative.log" 2>&1
cat "$out/derivative.log"
pkg_delete osqp-1.0.0
[ ! -e /usr/pkg/lib/libosqp.so ]
if pkg_info -e osqp-1.0.0; then exit 1; fi
if "$contract" qp > "$out/removed.log" 2>&1; then
    echo 'Removed solver remained usable.' >&2; exit 1
fi
pkg_add "$package"
pkg_admin check osqp > "$out/reinstalled-integrity.txt"
"$contract" qp > "$out/reinstalled.log" 2>&1
"$interrupt" > "$out/reinstalled-interrupt.log" 2>&1
"$derivative" > "$out/reinstalled-derivative.log" 2>&1
echo 'PASS: installed QP, infeasibility certificate, derivatives, real signal listener, removal and reinstallation'

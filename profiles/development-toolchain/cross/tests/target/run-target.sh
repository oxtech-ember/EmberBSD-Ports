#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; target execution of the cross-compiled native test sources.
set -eu
usage() { echo 'Usage: run-target.sh [--target aarch64|amd64] OUTPUT_DIRECTORY' >&2; exit 2; }
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
. "$here/target-options.sh"
[ "$#" -eq 1 ] || usage
case "$target" in aarch64) processor=aarch64;; amd64) processor=x86_64;; esac
[ "$(uname -s)" = NetBSD ] && [ "$(uname -p)" = "$processor" ] || {
    echo "Execute the built tests on $target EmberBSD/NetBSD." >&2; exit 2;
}
[ -z "${LD_LIBRARY_PATH:-}${LD_PRELOAD:-}" ] || { echo 'Remove loader overrides.' >&2; exit 2; }
mark_check() {
    [ -n "${EMBERBSD_ACCEPTANCE_NONCE:-}" ] || return 0
    case "$EMBERBSD_ACCEPTANCE_NONCE" in *[!A-Za-z0-9._-]*|'') echo 'Invalid acceptance nonce.' >&2; exit 2;; esac
    printf 'EMBERBSD-CHECK %s %s PASS\n' "$EMBERBSD_ACCEPTANCE_NONCE" "$1"
}
family=$(cat "$1/compiler-family.txt")
case "$family" in clang|gcc) ;; *) echo 'Invalid compiler family receipt.' >&2; exit 2;; esac
out=$(CDPATH= cd -- "$1" && pwd -P)
[ -f "$out/target.txt" ] && [ "$(cat "$out/target.txt")" = "$target" ] || {
    echo 'Compiled test target mismatch.' >&2; exit 2;
}
"$out/atomic-tls"
"$out/atomic-tls-lto"
mark_check target_c11
"$out/boundary" > "$out/loaded.txt"
ldd "$out/boundary" > "$out/ldd.txt"
sh "$out/check-runtime.sh" "$out"
mark_check target_cxx20
if [ -f "$out/os-tests.txt" ]; then
    [ ! -L "$out/os-tests.txt" ] && [ "$(cat "$out/os-tests.txt")" = yes ] || {
        echo 'Invalid OS test-suite receipt.' >&2; exit 2;
    }
    for test in libc-aliases base-loader-smoke fork-cas fork-cas-static; do
        [ -f "$out/$test" ] && [ -x "$out/$test" ] && [ ! -L "$out/$test" ] || {
            echo "Missing OS runtime regression: $test" >&2; exit 2;
        }
    done
    "$out/libc-aliases"
    mark_check libc_aliases
    "$out/base-loader-smoke"
    mark_check base_loader_smoke
    "$out/fork-cas"
    "$out/fork-cas-static"
    mark_check fork_cas
fi
cat "$out/loaded.txt"
echo "PASS: cross-built $family C11/C++20, atomics, threads, TLS, DSO unwind and selected compiler runtimes"

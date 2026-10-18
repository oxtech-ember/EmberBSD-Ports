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
out=$(CDPATH= cd -- "$1" && pwd -P)
[ -f "$out/target.txt" ] && [ "$(cat "$out/target.txt")" = "$target" ] || {
    echo 'Compiled test target mismatch.' >&2; exit 2;
}
"$out/atomic-tls"
"$out/atomic-tls-lto"
"$out/boundary" > "$out/loaded.txt"
ldd "$out/boundary" > "$out/ldd.txt"
sh "$out/check-runtime.sh" /usr/pkg/gcc16 "$out"
cat "$out/loaded.txt"
echo 'PASS: cross-built C11/C++20, atomics, threads, TLS, DSO unwind and selected GCC16 runtimes'

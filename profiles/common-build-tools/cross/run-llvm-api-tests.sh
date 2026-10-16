#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), installed shared LLVM target acceptance.
set -eu
[ "$#" = 2 ] || { echo 'Usage: run-llvm-api-tests.sh BUNDLE NEW_LOG_DIRECTORY' >&2; exit 2; }
[ "$(uname -s)" = NetBSD ] || { echo 'Run on NetBSD' >&2; exit 2; }
[ -z "${LD_LIBRARY_PATH:-}" ] && [ -z "${LD_PRELOAD:-}" ] || {
    echo 'Loader overrides are not permitted for installed-package acceptance' >&2; exit 2;
}
bundle=$(CDPATH= cd -- "$1" && pwd -P)
mkdir "$2"
logs=$(CDPATH= cd -- "$2" && pwd -P)
timeout=${TIMEOUT:-/usr/bin/timeout}
case "$timeout" in /*) ;; *) echo 'TIMEOUT must be absolute' >&2; exit 2;; esac
[ -x "$timeout" ]
[ -s "$bundle/artifacts.sha256" ] && [ -s "$bundle/runtime-library.sha256" ]
while read -r expected file; do
    [ "$(sha256 -q "$bundle/$file")" = "$expected" ] || {
        echo "Bundle hash mismatch: $file" >&2; exit 1;
    }
done < "$bundle/artifacts.sha256"
while read -r expected file; do
    [ "$(sha256 -q "$file")" = "$expected" ] || {
        echo "Installed LLVM hash mismatch: $file" >&2; exit 1;
    }
done < "$bundle/runtime-library.sha256"
arch=$(cat "$bundle/target-arch.txt")
case "$arch" in aarch64|x86_64) ;; *) echo 'Unsupported bundle CPU' >&2; exit 2;; esac
[ "$(uname -p)" = "$arch" ] || { echo 'Bundle CPU differs from the target' >&2; exit 2; }
uname -a > "$logs/platform.log"
for executable in llvm-c-api-test llvm-orc-test; do
    ldd "$bundle/bin/$executable" > "$logs/$executable.ldd.log" 2>&1
    if grep -q 'not found' "$logs/$executable.ldd.log"; then exit 1; fi
    grep -q '/usr/pkg/lib/libLLVM' "$logs/$executable.ldd.log"
    "$timeout" 60 "$bundle/bin/$executable" > "$logs/$executable.log" 2>&1
done
[ "$(grep -c '^PASS: JITLink/RTTI cycle ' "$logs/llvm-orc-test.log")" = 4 ]
status=0
"$timeout" 60 "$bundle/bin/llvm-orc-test" --missing-symbol > "$logs/missing-symbol.log" 2>&1 || status=$?
[ "$status" = 1 ] && grep -q 'EXPECTED-MISSING: SymbolsNotFound:' "$logs/missing-symbol.log"
printf '%s\n' 'PASS: C API/bitcode, four automatic JITLink lifecycles, missing-symbol exit 1; canonical shared LLVM without loader overrides'

#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Native Clang defaults: the LLVM runtimes.
# Usage: llvm-runtime-config.sh TARGET_LLVM_CONFIG NEW_OUTPUT
# The package's native NetBSD Clang uses the same runtimes as the EmberBSD
# SDK cross toolchain: compiler-rt builtins and CRT, libunwind and libc++
# from the base system. It needs no GCC.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 TARGET_LLVM_CONFIG NEW_OUTPUT" >&2; exit 2; }
llvm=$1 output=$2
fail() { echo "Invalid native Clang defaults: $*" >&2; exit 1; }
case "$llvm:$output" in *[!a-zA-Z0-9_./:+-]*) fail 'unsafe path' ;; esac
case "$llvm" in /*) ;; *) fail 'absolute LLVM config path required' ;; esac
[ -x "$llvm" ] || fail 'missing llvm-config'
[ ! -e "$output" ] && [ ! -L "$output" ] || fail 'output exists'
triple=$("$llvm" --host-target)
case "$triple" in aarch64-unknown-netbsd*|x86_64-unknown-netbsd*) ;; *) fail 'native target must be NetBSD' ;; esac
case "$triple" in *[!a-zA-Z0-9_.+-]*) fail 'unsafe target' ;; esac
mkdir "$output"
{
    echo '# Native LLVM runtimes, as in the SDK; same-triple SDKs use --no-default-config.'
    echo '--rtlib=compiler-rt'
    echo '--unwindlib=libunwind'
    echo '-stdlib=libc++'
} > "$output/$triple.cfg"
printf 'etc/clang/%s.cfg\n' "$triple" > "$output/PLIST"

#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# Read actual exported build commands; do not build compiler-rt.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 BMAKE PREPARED_PKGSRC" >&2; exit 2; }
bmake=$1
tree=$(CDPATH= cd -- "$2" && pwd)
fail() { echo "FAIL: $*" >&2; exit 1; }
check() {
    package=$1 native=$2 target=$3
    shift 3
    commands=$("$bmake" -C "$tree/lang/$package" MAKECONF=/dev/null \
        TOOLBASE=/native-tools LOCALBASE=/package-dependencies PREFIX=/package-target \
        CROSS_LOCALBASE=/cross-target EMBERBSD_CROSS_HOST_PREFIX=/cross-host \
        EMBERBSD_SDK_SOURCE=/sdk EMBERBSD_FREESTANDING_HOST_PREFIX=/unsupported-host \
        TOOL_PYTHONBIN="$native/bin/python3.15" MAKE_JOBS=4 \
        PKGSRC_COMPILER=clang CLANGBASE=/native-tools _CLANG_VERSION=23.1.4 \
        PKG_ADMIN=/usr/bin/true PKG_INFO=/usr/bin/true PKGVULNDIR=/unused \
        ACCEPTABLE_LICENSES=apache-2.0 "$@" -n do-build)
    [ "$(printf '%s\n' "$commands" | grep -c "^$native/bin/python3.15 ")" -eq 2 ] ||
        fail "$package does not use the native Python"
    case "$commands" in *" --patch $native/bin/gpatch"*) ;; *) fail "$package patch tool escaped native prefix";; esac
    case "$commands" in *" --host-prefix $native "*) ;; *) fail "$package runtime tools escaped native prefix";; esac
    case "$commands" in *" --target $target "*" --jobs 4"*) ;; *) fail "$package lost its target or job budget";; esac
    case "$commands" in */unsupported-host*) fail "$package accepts the removed generic host setting";; esac
}
check riscv32-elf-compiler-rt /native-tools riscv32-unknown-elf EMBERBSD_WASI_HOST_PREFIX=/wrong-wasi
check wasi-compiler-rt /native-tools wasm32-wasip1
check wasi-compiler-rt /wasi-compat wasm32-wasip1 EMBERBSD_WASI_HOST_PREFIX=/wasi-compat
echo 'PASS: freestanding recipes use native TOOLBASE tools and retain the WASI prefix input'

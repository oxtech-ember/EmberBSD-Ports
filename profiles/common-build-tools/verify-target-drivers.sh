#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
# The profile has already selected and validated the compiler family and SDK.
set -eu
[ "$#" -eq 4 ] || { echo 'usage: verify-target-drivers.sh CC CXX GNU_TRIPLET RUST_TRIPLE' >&2; exit 2; }
cc=$1 cxx=$2 gnu=$3 rust=$4
cc_target=$("$cc" -dumpmachine)
cxx_target=$("$cxx" -dumpmachine)
case "$cc_target" in "$gnu"|"$rust") ;; *) echo 'unexpected C compiler target' >&2; exit 1 ;; esac
[ "$cc_target" = "$cxx_target" ] || { echo 'C and C++ target mismatch' >&2; exit 1; }
driver_version() {
    # GCC exposes a full minor version here; Clang accepts -dumpversion only.
    if value=$("$1" -dumpfullversion 2>/dev/null) && [ -n "$value" ]; then
        printf '%s\n' "$value"
    else
        "$1" -dumpversion
    fi
}
cc_version=$(driver_version "$cc")
cxx_version=$(driver_version "$cxx")
[ -n "$cc_version" ] && [ "$cc_version" = "$cxx_version" ] || {
    echo 'C and C++ compiler version mismatch' >&2; exit 1;
}

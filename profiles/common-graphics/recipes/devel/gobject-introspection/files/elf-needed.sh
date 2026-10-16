#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Resolve SONAMEs without executing target ldd.
set -eu
[ "$#" = 1 ] || { echo 'Usage: elf-needed.sh ELF_BINARY' >&2; exit 2; }
: "${EMBERBSD_GI_READELF:?Set the absolute target readelf path}"
case "$EMBERBSD_GI_READELF" in /*) ;; *) exit 2 ;; esac
case ${EMBERBSD_GI_TARGET-aarch64} in
    aarch64) machine=AArch64 ;;
    amd64) machine='Advanced Micro Devices X86-64' ;;
    *) echo 'unsupported GI target' >&2; exit 2 ;;
esac
header=$("$EMBERBSD_GI_READELF" -h "$1")
printf '%s\n' "$header" | grep -q 'Class:.*ELF64' || exit 1
printf '%s\n' "$header" | grep -q 'Data:.*little endian' || exit 1
[ "$(printf '%s\n' "$header" | sed -n 's/^[[:space:]]*Machine:[[:space:]]*//p')" = "$machine" ] || exit 1
result=$("$EMBERBSD_GI_READELF" -d "$1")
printf '%s\n' "$result" | sed -n 's/.*(NEEDED).*\[\([^]]*\)\].*/\1/p'

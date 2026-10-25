#!/bin/sh
# Origin: EmberBSD; AI-assisted installed libdrm checker fixture runner.
# SPDX-License-Identifier: BSD-2-Clause
set -eu
[ "$#" -eq 1 ] || { echo 'Usage: libdrm-amdgpu-pci-check.sh LIBDRM_SOURCE' >&2; exit 2; }
: "${CC:?set CC to the absolute path of a GCC16 compiler}"
case "$CC" in
	/*) ;;
	*) echo 'CC must be an absolute GCC16 compiler path' >&2; exit 2 ;;
esac
[ -x "$CC" ] || { echo "compiler is not executable: $CC" >&2; exit 2; }
compiler_version=$("$CC" -dumpfullversion -dumpversion) || exit 2
case "$compiler_version" in
	16|16.*) ;;
	*) echo "GCC 16 required; compiler reports $compiler_version" >&2; exit 2 ;;
esac
compiler_target=$("$CC" -dumpmachine) || exit 2
compiler_banner=$("$CC" --version) || exit 2
case "$compiler_banner" in
	*clang*|*Clang*|*CLANG*)
		echo 'Clang is not accepted for the GCC16 fixture' >&2
		exit 2 ;;
esac
printf 'Compiler path: %s\nCompiler version: %s\nCompiler target: %s\n' \
	"$CC" "$compiler_version" "$compiler_target"
source=$1
recipe=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
[ -f "$source/xf86drm.h" ] || { echo "missing libdrm header: $source/xf86drm.h" >&2; exit 1; }
work=$(mktemp -d "${TMPDIR:-/tmp}/libdrm-amdgpu-pci-check.XXXXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
"$CC" -std=c11 -D_POSIX_C_SOURCE=200809L -D_NETBSD_SOURCE \
	-Wall -Wextra -Werror \
    -I"$source" -I"$source/include/drm" \
    "$recipe/libdrm-amdgpu-pci-check.c" -o "$work/check"
"$work/check"

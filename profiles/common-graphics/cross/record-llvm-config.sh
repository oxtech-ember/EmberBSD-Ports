#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Run on the target after staging full LLVM.
set -eu
usage() { echo 'usage: record-llvm-config.sh [--target aarch64|amd64] TARGET_LLVM_CONFIG NEW_OUTPUT' >&2; exit 1; }
# Keep this target-side capture standalone: no Ports checkout is required.
target=aarch64
case ${1:-} in
    --target) [ "$#" -ge 2 ] || usage; target=$2; shift 2;;
esac
case "$target" in
    aarch64) processor=aarch64; triplet=aarch64--netbsd; machine=AArch64;;
    amd64) processor=x86_64; triplet=x86_64--netbsd; machine='Advanced Micro Devices X86-64';;
    *) usage;;
esac
[ "$#" -eq 2 ] || usage
case "$1" in --*) usage;; esac
[ "$(uname -s)" = NetBSD ] && [ "$(uname -p)" = "$processor" ] || {
    echo 'capture must execute on the selected NetBSD target' >&2
    exit 1
}
llvm_config=$1
output=$2
case "$llvm_config:$output" in /*:/*) ;; *) echo 'absolute paths required' >&2; exit 1;; esac
[ -x "$llvm_config" ] && [ ! -e "$output" ] && [ ! -L "$output" ] || { echo 'executable missing or output exists' >&2; exit 1; }
readelf=${READELF:-readelf}
command -v "$readelf" >/dev/null || { echo 'Set READELF to a target-native diagnostic executable' >&2; exit 1; }
header=$("$readelf" -h "$llvm_config") || exit 1
printf '%s\n' "$header" | grep -Eq 'Class:[[:space:]]+ELF64' &&
printf '%s\n' "$header" | grep -Eq 'Data:.*little endian' &&
printf '%s\n' "$header" | grep -Eq 'Type:[[:space:]]+(EXEC|DYN)' &&
[ "$(printf '%s\n' "$header" | sed -n 's/^[[:space:]]*Machine:[[:space:]]*//p')" = "$machine" ] || {
    echo 'llvm-config ELF does not match selected target' >&2; exit 1;
}
version=$("$llvm_config" --version)
host_target=$("$llvm_config" --host-target)
[ "$version" = 23.1.3 ] && printf '%s\n' "$host_target" | grep -Eq "^$processor-(unknown)?-netbsd(11(\.[0-9]+)*)?$" || {
    echo 'llvm-config version/NetBSD target triple mismatch' >&2; exit 1;
}
mkdir "$output"
printf 'target=%s\ntriplet=%s\nprocessor=%s\n' "$target" "$triplet" "$processor" > "$output/target.txt"
uname -a > "$output/platform"
sha256 -q "$llvm_config" > "$output/executable.sha256"
printf '%s\n' "$version" > "$output/version"
printf '%s\n' "$host_target" > "$output/host-target"
for option in has-rtti assertion-mode targets-built components prefix cppflags cflags cxxflags ldflags; do
    "$llvm_config" "--$option" > "$output/$option"
done
for option in shared-mode libs libnames libfiles system-libs; do
    "$llvm_config" --link-shared "--$option" bitwriter engine mcdisassembler mcjit core executionengine scalaropts transformutils instcombine native orcjit > "$output/$option"
done
printf '%s\n' "$llvm_config" > "$output/executable"
printf '%s\n' 'complete' > "$output/status"

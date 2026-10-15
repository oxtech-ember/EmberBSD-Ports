#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check official target data with the host Rust.
set -eu
[ "$#" -eq 5 ] || { echo 'Usage: check.sh HOST_PREFIX SOURCE STAGED_PREFIX NEW_OUTPUT TARGET_READELF' >&2; exit 2; }
host=$1 source=$2 stage=$3 work=$4 readelf=$5
fail() { echo "FAIL: $*" >&2; exit 1; }
for item in "$@"; do
    case "$item" in /*) ;; *) fail 'absolute paths required';; esac
    case "$item" in *[!A-Za-z0-9_./+-]*) fail 'unsupported path characters';; esac
done
host=$(CDPATH= cd -- "$host" && pwd -P)
source=$(CDPATH= cd -- "$source" && pwd -P)
stage=$(CDPATH= cd -- "$stage" && pwd -P)
[ ! -e "$work" ] && [ ! -L "$work" ] || fail 'new output directory required'
work=$(CDPATH= cd -- "$(dirname "$work")" && pwd -P)/$(basename "$work")
for input in "$host" "$source" "$stage"; do
    case "$work/" in "$input/"*) fail 'check output overlaps a provider';; esac
    case "$input/" in "$work/"*) fail 'provider is inside check output';; esac
done
[ -x "$host/bin/rustc" ] && [ -x "$readelf" ] || fail 'host rustc and target readelf are required'
[ "$(cat "$source/components")" = rust-std-x86_64-unknown-netbsd ] || fail 'wrong upstream component'
[ "$(cat "$source/git-commit-hash")" = b940084d7eb6a299eb4bfeb8e34901bc051e7ac4 ] || fail 'wrong upstream compiler commit'
unset RUSTC_BOOTSTRAP RUSTFLAGS CARGO_ENCODED_RUSTFLAGS RUSTC_WRAPPER RUSTC_WORKSPACE_WRAPPER
unset DYLD_LIBRARY_PATH DYLD_FRAMEWORK_PATH DYLD_INSERT_LIBRARIES
LC_ALL=C
export LC_ALL
mkdir "$work"
"$host/bin/rustc" -vV > "$work/compiler.txt"
grep -qx 'rustc 1.99.0 (b940084d7 2026-09-28)' "$work/compiler.txt" && \
    grep -qx 'commit-hash: b940084d7eb6a299eb4bfeb8e34901bc051e7ac4' "$work/compiler.txt" || fail 'official Rust 1.99.0 required'
grep -Eq '^host: (aarch64|x86_64)-apple-darwin$' "$work/compiler.txt" || fail 'official macOS host compiler required'
component=lib/rustlib/x86_64-unknown-netbsd/lib
upstream=$source/rust-std-x86_64-unknown-netbsd
sed 's/^file://' "$upstream/manifest.in" | sort > "$work/expected-files"
(cd "$stage" && find "$component" -type f -print | sort) > "$work/staged-files"
cmp -s "$work/expected-files" "$work/staged-files" || fail 'target component manifest differs'
[ -z "$(find "$stage/$component" -type l -print)" ] || fail 'unexpected target component symlink'
while IFS= read -r file; do
    case "$file" in "$component/"*) ;; *) fail 'invalid upstream component path';; esac
    case "$file" in *../*) fail 'invalid upstream component path';; esac
    cmp -s "$upstream/$file" "$stage/$file" || fail 'target component differs from the upstream payload'
done < "$work/expected-files"
for name in std core alloc panic_unwind; do
    for extension in rmeta rlib; do
        set -- "$stage/$component/lib$name-"*."$extension"
        [ "$#" -eq 1 ] && [ -s "$1" ] || fail "missing/duplicate $name.$extension"
    done
done
set -- "$stage/$component/libstd-"*.so
[ "$#" -eq 1 ] && [ -s "$1" ] || fail 'missing/duplicate target libstd.so'
"$readelf" -h "$1" > "$work/elf-header.txt"
grep -q 'Machine:.*Advanced Micro Devices X86-64' "$work/elf-header.txt" && \
    grep -q 'Class:.*ELF64' "$work/elf-header.txt" || fail 'target std must be x86_64 ELF64'
"$readelf" -d "$1" > "$work/dynamic.txt"
sed -n 's/.*(NEEDED).*\[\(.*\)\]/\1/p' "$work/dynamic.txt" | sort > "$work/needed.txt"
printf 'libc.so.12\nlibgcc_s.so.1\nlibpthread.so.1\n' > "$work/expected-needed.txt"
cmp -s "$work/needed.txt" "$work/expected-needed.txt" || fail 'unexpected target std providers'
sed -n 's/.*(RPATH).*\[\(.*\)\]/\1/p' "$work/dynamic.txt" > "$work/rpath.txt"
printf '$ORIGIN/../lib\n' > "$work/expected-rpath.txt"
cmp -s "$work/rpath.txt" "$work/expected-rpath.txt" || fail 'unexpected official target std RPATH'
printf 'pub fn pointer_size() -> usize { core::mem::size_of::<usize>() + std::mem::align_of::<usize>() }\n' > "$work/metadata.rs"
"$host/bin/rustc" --crate-name ember_std_metadata_check --edition=2024 --crate-type=lib \
    --target x86_64-unknown-netbsd --sysroot "$stage" --emit=metadata \
    "$work/metadata.rs" -o "$work/metadata.rmeta"
[ -s "$work/metadata.rmeta" ] || fail 'host Rust produced no target metadata'
echo 'PASS: complete official x86_64 target component, ELF dependencies and host Rust metadata import'

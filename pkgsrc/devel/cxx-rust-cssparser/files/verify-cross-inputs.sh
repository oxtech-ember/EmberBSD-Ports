#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Check the shared native Rust provider and its target std before Cargo runs.
set -eu
[ "$#" -eq 5 ] || { echo 'Usage: verify-cross-inputs.sh HOST_PREFIX RUST_TARGET GNU_TRIPLET WRAPPERS PROBE_OUTPUT' >&2; exit 2; }
host=$1 target=$2 triplet=$3 wrappers=$4 probe=$5
fail() { echo "$*" >&2; exit 1; }
case "$target:$triplet" in
    aarch64-unknown-netbsd:aarch64--netbsd|x86_64-unknown-netbsd:x86_64--netbsd) ;;
    *) fail 'Unsupported or mixed Rust/GCC cross target.';;
esac
for input in "$host" "$wrappers" "$probe"; do
    case "$input" in /*) ;; *) fail 'Absolute provider and probe paths required.';; esac
    case "$input" in *[!A-Za-z0-9_./+-]*) fail 'Unsupported provider path characters.';; esac
done
host=$(CDPATH= cd -- "$host" && pwd -P)
rustc=$host/bin/rustc cargo=$host/bin/cargo
[ -x "$rustc" ] && [ -x "$cargo" ] || fail 'The shared native rust-bin provider is missing.'
version=$("$rustc" -vV)
printf '%s\n' "$version" | grep -qx 'rustc 1.99.1 (58cf8f9c3 2026-10-13)' || fail 'The shared official Rust 1.99.1 compiler is required.'
printf '%s\n' "$version" | grep -qx 'commit-hash: 58cf8f9c35b355199727627d07ae34a4e2846d67' || fail 'Rust compiler producer mismatch.'
"$cargo" -V | grep -q '^cargo 1[.]99[.]1 ' || fail 'The matching shared Cargo 1.99.1 is required.'
native=$(printf '%s\n' "$version" | sed -n 's/^host: //p')
case "$native" in ''|*[!a-zA-Z0-9_-]*) fail 'Invalid Rust build-host triple.';; esac
[ "$native" != "$target" ] || fail 'This recipe requires a build-host compiler distinct from the target.'
for driver in gcc g++; do
    compiler=$wrappers/$triplet-$driver
    [ -x "$compiler" ] || fail "Missing target wrapper: $driver"
    [ "$("$compiler" -dumpmachine)" = "$triplet" ] || fail 'Target wrapper architecture mismatch.'
    [ "$("$compiler" -dumpfullversion)" = 16.2.0 ] || fail 'Target wrapper must use GCC 16.2.0.'
done
component=$("$rustc" --target "$target" --print target-libdir)
[ -d "$component" ] || fail 'Missing target std in the shared Rust prefix.'
component=$(CDPATH= cd -- "$component" && pwd -P)
[ "$component" = "$host/lib/rustlib/$target/lib" ] || fail 'Target std resolves outside the shared Rust provider.'
for library in std core; do
    set -- "$component/lib$library-"*.rlib
    [ "$#" -eq 1 ] && [ -s "$1" ] || fail "Missing or ambiguous target $library rlib."
done
# This uses the actual compiler metadata reader. E0514 is a compatibility
# failure, not an invitation to rewrite crate metadata or set RUSTC_BOOTSTRAP.
printf 'pub fn target_std_check() -> std::string::String { std::string::String::new() }\n' |
    "$rustc" --crate-type=lib --target "$target" --emit=metadata --edition=2024 -o "$probe" -
[ -s "$probe" ] || fail 'The target std metadata probe produced no output.'
printf '%s\n' "$native"

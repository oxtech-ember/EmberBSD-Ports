#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Snapshot only the installed Rust provider.
set -eu
[ "$#" -eq 2 ] || { echo 'Usage: isolate-host-rust.sh HOST_PREFIX NEW_SNAPSHOT' >&2; exit 2; }
host=$1 snapshot=$2
for path in "$host" "$snapshot"; do
    case "$path" in /*) ;; *) exit 2;; esac
    case "$path" in *[!a-zA-Z0-9_./+-]*) exit 2;; esac
done
host=$(CDPATH= cd -- "$host" && pwd -P)
parent=$(CDPATH= cd -- "$(dirname "$snapshot")" && pwd -P)
snapshot=$parent/$(basename "$snapshot")
case "$snapshot/" in "$host/"*) echo 'Snapshot overlaps installed provider' >&2; exit 2;; esac
case "$host/" in "$snapshot/"*) echo 'Snapshot contains installed provider' >&2; exit 2;; esac
[ ! -e "$snapshot" ] && [ ! -L "$snapshot" ] || { echo 'Snapshot already exists' >&2; exit 2; }
# x.py prepends the compiler's lib directory to DYLD_LIBRARY_PATH. A shared
# pkgsrc prefix also holds GNU iconv, which must not replace Apple's iconv
# required by the unmodified official compiler. Keep those unrelated DSOs out
# of this temporary bootstrap input, without changing or rebuilding Rust.
mkdir "$snapshot"
"$host/sbin/pkg_info" -qL 'rust-bin-1.99.1{,nb[0-9]*}' > "$snapshot/package-files.txt"
while IFS= read -r file; do
    case "$file" in "$host/"*) relative=${file#"$host/"};; '') continue;; *) exit 2;; esac
    case "$relative" in
        bin/rustc|bin/cargo|bin/rustdoc|lib/rustlib/aarch64-apple-darwin/*) ;;
        lib/*.dylib) case "${relative#lib/}" in */*) continue;; esac;;
        *) continue;;
    esac
    case "$relative" in *[!a-zA-Z0-9_./+-]*) exit 2;; esac
    [ -f "$file" ] && [ ! -L "$file" ] || { echo "Unexpected Rust input: $relative" >&2; exit 1; }
    mkdir -p "$snapshot/$(dirname "$relative")"
    cp -p "$file" "$snapshot/$relative"
    cmp "$file" "$snapshot/$relative"
done < "$snapshot/package-files.txt"
"$host/bin/rustc" -vV > "$snapshot/installed-compiler.txt"
DYLD_LIBRARY_PATH="$snapshot/lib" "$snapshot/bin/rustc" -vV > "$snapshot/copied-compiler.txt"
cmp "$snapshot/installed-compiler.txt" "$snapshot/copied-compiler.txt"
[ "$("$snapshot/bin/rustc" --print sysroot)" = "$snapshot" ]
echo 'PASS: byte-identical installed Rust bootstrap inputs in an isolated loader directory'

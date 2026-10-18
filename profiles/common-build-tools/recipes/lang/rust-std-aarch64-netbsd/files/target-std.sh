#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Package lifecycle for source-built target std.
set -eu
[ "$#" -ge 6 ] || { echo 'target-std.sh MODE SOURCE WORK HOST CROSS SYSROOT [ARG]' >&2; exit 2; }
mode=$1 source=$2 work=$3 host=$4 cross=$5 sysroot=$6
shift 6
# Paths also enter TOML and wrapper scripts: reject unsupported spellings.
for path in "$source" "$work" "$host" "$cross" "$sysroot"; do
    case "$path" in /*) ;; *) echo 'absolute paths required' >&2; exit 2 ;; esac
    case "$path" in *[!a-zA-Z0-9_./+-]*) echo 'unsupported path characters' >&2; exit 2 ;; esac
    [ -d "$path" ] || { echo "missing input directory: $path" >&2; exit 2; }
done
# Canonicalize directories and the compiler facade before any helper writes.
source=$(CDPATH= cd -- "$source" && pwd -P)
work=$(CDPATH= cd -- "$work" && pwd -P)
host=$(CDPATH= cd -- "$host" && pwd -P)
cross=$(CDPATH= cd -- "$cross" && pwd -P)
sysroot=$(CDPATH= cd -- "$sysroot" && pwd -P)
compiler=$cross/bin/aarch64--netbsd-gcc
links=0
while [ -L "$compiler" ]; do
    links=$((links + 1))
    [ "$links" -le 40 ] || exit 2
    link=$(readlink "$compiler")
    case "$link" in /*) compiler=$link ;; *) compiler=$(dirname "$compiler")/$link ;; esac
done
compiler_dir=$(CDPATH= cd -- "$(dirname "$compiler")" && pwd -P)
cross_provider=$(dirname "$compiler_dir")
for input in "$host" "$cross" "$cross_provider" "$sysroot"; do
    for output in "$source" "$work"; do
        case "$output/" in "$input/"*) echo 'work/source overlaps an input provider' >&2; exit 2 ;; esac
        case "$input/" in "$output/"*) echo 'input provider is inside work/source' >&2; exit 2 ;; esac
    done
done
for path in "$source" "$work" "$host" "$cross" "$sysroot"; do
    case "$path" in *[!a-zA-Z0-9_./+-]*) echo 'unsupported resolved path characters' >&2; exit 2 ;; esac
done
# Never allow callers' target flags to affect native bootstrap/proc macros.
unset RUSTFLAGS CARGO_ENCODED_RUSTFLAGS CARGO_BUILD_TARGET RUSTC_BOOTSTRAP
unset RUSTC_WRAPPER RUSTC_WORKSPACE_WRAPPER CARGO_TARGET_DIR
unset DYLD_LIBRARY_PATH DYLD_FRAMEWORK_PATH DYLD_INSERT_LIBRARIES
export LC_ALL=C
export CARGO_NET_OFFLINE=true CARGO_HOME="$work/cargo-home" TMPDIR="$work/tmp"
cc=$cross/bin/aarch64--netbsd-gcc
cxx=$cross/bin/aarch64--netbsd-g++
ar=$cross/bin/aarch64--netbsd-ar
readelf=$cross/bin/aarch64--netbsd-readelf
crt=$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0
case "$mode" in
preflight)
    [ "$#" -eq 0 ] || exit 2
    ;;
configure)
    [ "$#" -eq 0 ] || exit 2
    grep 'pub fn cp_link_r_excluding' "$source/src/bootstrap/src/lib.rs" > /dev/null
    "$host/bin/rustc" -vV > "$work/compiler.txt"
    grep -qx 'rustc 1.99.1 (58cf8f9c3 2026-10-13)' "$work/compiler.txt"
    grep -qx 'commit-hash: b940084d7eb6a299eb4bfeb8e34901bc051e7ac4' "$work/compiler.txt"
    grep -qx 'host: aarch64-apple-darwin' "$work/compiler.txt"
    "$host/bin/cargo" -V > "$work/cargo.txt"
    grep '^cargo 1\.99\.0 ' "$work/cargo.txt"
    [ "$("$cc" -dumpfullversion)" = 16.2.0 ]
    for file in "$cxx" "$ar" "$readelf" "$crt/crtbeginS.o" "$sysroot/usr/include/stdio.h" \
        "$sysroot/usr/pkg/gcc16/lib/libgcc_s.so.1" "$sysroot/usr/lib/libc.so"; do
        [ -f "$file" ] || { echo "missing target input: $file" >&2; exit 1; }
    done
    mkdir -p "$work/tmp" "$work/cargo-home"
    sh "$(dirname "$0")/isolate-host-rust.sh" "$host" "$work/host-rust"
    for pair in "cc:$cc" "cxx:$cxx"; do
        name=${pair%%:*} compiler=${pair#*:}
        printf '#!/bin/sh\nexec "%s" "--sysroot=%s" "-B%s/" "-L%s/usr/pkg/gcc16/lib" -Wl,-rpath,/usr/pkg/gcc16/lib "$@"\n' \
            "$compiler" "$sysroot" "$crt" "$sysroot" > "$work/netbsd-$name"
        chmod 755 "$work/netbsd-$name"
    done
    cat > "$source/bootstrap.toml" <<EOF
change-id = "ignore"
[build]
build = "aarch64-apple-darwin"
host = ["aarch64-apple-darwin"]
target = ["aarch64-unknown-netbsd"]
rustc = "$work/host-rust/bin/rustc"
cargo = "$work/host-rust/bin/cargo"
local-rebuild = true
locked-deps = true
vendor = true
extended = false
jobs = 2
build-dir = "$work/out"
[llvm]
download-ci-llvm = false
[rust]
channel = "stable"
download-rustc = false
remap-debuginfo = true
[target.aarch64-unknown-netbsd]
cc = "$work/netbsd-cc"
cxx = "$work/netbsd-cxx"
ar = "$ar"
linker = "$work/netbsd-cc"
EOF
    ;;
build)
    [ "$#" -eq 1 ] && [ -x "$1" ] || exit 2
    python=$1
    cd "$source"
    "$python" x.py build library --stage 0 --target aarch64-unknown-netbsd -j2 --dry-run > "$work/std-plan.log" 2>&1 || {
        cat "$work/std-plan.log"; exit 1;
    }
    cat "$work/std-plan.log"
    grep 'Building stage0 library artifacts' "$work/std-plan.log" > /dev/null
    if grep -E 'Building (stage[1-9]|LLVM|LLD|stage0 compiler)' "$work/std-plan.log"; then
        echo 'refusing unexpected compiler/backend build' >&2; exit 1
    fi
    "$python" x.py build library --stage 0 --target aarch64-unknown-netbsd -j2
    ;;
check)
    [ "$#" -eq 1 ] && [ -d "$1" ] || exit 2
    component=$1
    for name in std core alloc panic_unwind; do
        for extension in rmeta rlib; do
            set -- "$component/lib$name-"*."$extension"
            [ "$#" -eq 1 ] && [ -s "$1" ] || { echo "missing/duplicate $name.$extension" >&2; exit 1; }
        done
    done
    set -- "$component/libstd-"*.so
    [ "$#" -eq 1 ] && [ -s "$1" ] || exit 1
    "$readelf" -h "$1" > "$work/std-elf-header.txt"
    grep 'Machine:.*AArch64' "$work/std-elf-header.txt" > /dev/null
    grep 'Class:.*ELF64' "$work/std-elf-header.txt" > /dev/null
    "$readelf" -d "$1" > "$work/std-dynamic.txt"
    sed -n 's/.*(NEEDED).*\[\(.*\)\]/\1/p' "$work/std-dynamic.txt" | sort > "$work/std-needed.txt"
    printf 'libc.so.12\nlibgcc_s.so.1\nlibpthread.so.1\n' > "$work/std-needed-expected.txt"
    cmp "$work/std-needed.txt" "$work/std-needed-expected.txt"
    sed -n 's/.*(RPATH).*\[\(.*\)\]/\1/p' "$work/std-dynamic.txt" > "$work/std-rpath.txt"
    printf '/usr/pkg/gcc16/lib:$ORIGIN/../lib\n' > "$work/std-rpath-expected.txt"
    cmp "$work/std-rpath.txt" "$work/std-rpath-expected.txt"
    for file in usr/lib/libc.so.12 usr/lib/libpthread.so.1 usr/pkg/gcc16/lib/libgcc_s.so.1; do
        "$readelf" -h "$sysroot/$file" > "$work/std-provider-header.txt"
        grep 'Machine:.*AArch64' "$work/std-provider-header.txt" > /dev/null
        grep 'Class:.*ELF64' "$work/std-provider-header.txt" > /dev/null
    done
    echo 'PASS: complete std/core/alloc/unwind metadata, target ELF and three AArch64 providers'
    ;;
*) exit 2 ;;
esac

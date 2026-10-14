#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD, AI-assisted.
# Run on the build host. SOURCE must be the pinned, unpatched llama.cpp tree.
set -eu
[ "$#" -eq 3 ] || {
    echo 'Usage: check-ggml-alloc-oom.sh SOURCE CONFIGURED_BUILD NEW_WORK' >&2
    exit 2
}
source_dir=$(CDPATH= cd -- "$1" && pwd -P)
build_dir=$(CDPATH= cd -- "$2" && pwd -P)
work=$3
tests=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
patch_file=$tests/../../../pkgsrc/local-ai/llama-cpp/patches/patch-ggml_src_ggml-alloc.c
compiler=${CC:-cc}
case "$work" in /*) ;; *) echo 'NEW_WORK must be absolute.' >&2; exit 2;; esac
[ ! -e "$work" ] && [ ! -L "$work" ]
[ -f "$build_dir/ggml/src/ggml-version.h" ]
mkdir -p "$work/baseline/ggml/src" "$work/patched/ggml/src"
cp "$source_dir/ggml/src/ggml-alloc.c" "$work/baseline/ggml/src/"
cp "$source_dir/ggml/src/ggml-alloc.c" "$work/patched/ggml/src/"
patch -f -F0 -p0 -d "$work/patched" < "$patch_file" > "$work/patch.log"
"$compiler" --version > "$work/compiler.txt"
sha256sum "$source_dir/ggml/src/ggml-alloc.c" "$patch_file" \
    "$tests/ggml-alloc-oom.c" > "$work/inputs.sha256"
# Use upstream's C warnings, including its existing unused-function setting.
# The include exposes private entry points; section GC removes unrelated code.
set -- -std=gnu11 -O2 -g -D_GNU_SOURCE -D_XOPEN_SOURCE=600 \
    -DGGML_SCHED_MAX_COPIES=4 -ffunction-sections -fdata-sections \
    -Wshadow -Wstrict-prototypes -Wpointer-arith -Wmissing-prototypes \
    -Werror=implicit-int -Werror=implicit-function-declaration \
    -Wall -Wextra -Wpedantic -Wcast-qual -Wno-unused-function -Wdouble-promotion \
    -I"$source_dir/ggml/src" -I"$source_dir/ggml/include" \
    -I"$build_dir/ggml/src"
"$compiler" "$@" -c "$source_dir/ggml/src/ggml.c" -o "$work/ggml.o" \
    > "$work/ggml-build.log" 2>&1
for variant in baseline patched; do
    for mode in debug release; do
        case "$mode" in debug) define=-UNDEBUG;; release) define=-DNDEBUG;; esac
        "$compiler" -I"$work/$variant/ggml/src" "$@" "$define" \
            "$tests/ggml-alloc-oom.c" "$work/ggml.o" -Wl,--gc-sections \
            -o "$work/$variant-$mode" > "$work/$variant-$mode-build.log" 2>&1
        status=0
        "$work/$variant-$mode" > "$work/$variant-$mode.log" 2>&1 || status=$?
        if [ "$variant" = baseline ]; then
            [ "$status" -ne 0 ]
            [ "$(grep -c 'expected GGML_ASSERT and SIGABRT' "$work/$variant-$mode.log")" -eq 2 ]
        else
            [ "$status" -eq 0 ]
        fi
    done
done
valgrind --tool=memcheck --leak-check=full --show-leak-kinds=all \
    --errors-for-leak-kinds=definite,indirect --error-exitcode=125 \
    "$work/patched-release" --success-only > "$work/memcheck.log" 2>&1
echo 'PASS: real upstream malloc/calloc OOM paths fail; patched debug/release paths abort with the correct diagnostic.'
echo 'PASS: the successful real allocator path passes Valgrind Memcheck.'

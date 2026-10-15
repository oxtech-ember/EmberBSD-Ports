#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
set -eu
[ "$#" -eq 2 ] || {
    echo "Usage: $0 NEW_OUTPUT MESA_DRM_UAPI_DIRECTORY" >&2
    exit 2
}
work=$1 headers=$2
[ ! -e "$work" ] || { echo 'Output exists' >&2; exit 2; }
mkdir "$work"
dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
: "${CC:=cc}"
"$CC" --version > "$work/compiler.txt"
for mode in normal sanitized; do
    sanitizer=
    [ "$mode" = normal ] || sanitizer='-fsanitize=address,undefined -fno-omit-frame-pointer'
    # The production TU uses real UAPI structures. Only its syscall names change.
    "$CC" -std=c11 -O1 -g -Wall -Wextra -Werror -I"$headers" $sanitizer \
        -Dmain=v3d_bo_alloc_main -Dopen=test_open -Dioctl=test_ioctl -Dclose=test_close \
        -c "$dir/../cross/v3d-bo-alloc.c" -o "$work/cli-$mode.o"
    "$CC" -std=c11 -O1 -g -Wall -Wextra -Werror -I"$headers" $sanitizer \
        "$dir/v3d-bo-alloc.c" "$work/cli-$mode.o" -o "$work/contract-$mode"
    ASAN_OPTIONS=halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 \
        "$work/contract-$mode" > "$work/$mode.log" 2>&1
    cat "$work/$mode.log"
done

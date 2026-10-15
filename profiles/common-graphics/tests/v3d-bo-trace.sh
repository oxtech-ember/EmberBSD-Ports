#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Run real-wrapper host contracts with pristine libdrm and Mesa UAPI headers.
set -eu
[ "$#" -eq 3 ] || {
    echo "Usage: $0 NEW_OUTPUT LIBDRM_HEADER_DIRECTORY MESA_DRM_UAPI_DIRECTORY" >&2
    exit 2
}
work=$1 drm=$2 mesa=$3
[ ! -e "$work" ] || { echo 'Output exists' >&2; exit 2; }
mkdir "$work"
source=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/v3d-bo-trace.c
: "${CC:=cc}"
"$CC" --version > "$work/compiler.txt"
"$CC" -std=c11 -O1 -g -Wall -Wextra -Werror -pthread -I"$drm" -I"$mesa" \
    "$source" -o "$work/contract"
"$work/contract" > "$work/contract.log" 2>&1
"$CC" -std=c11 -O1 -g -Wall -Wextra -Werror -pthread -I"$drm" -I"$mesa" \
    -fsanitize=address,undefined -fno-omit-frame-pointer \
    "$source" -o "$work/contract-sanitized"
# ASan intercepts write() before the kernel can reject an invalid input pointer.
# The normal contract above covers that EFAULT case. Other cases run sanitized.
ASAN_OPTIONS=halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 \
    "$work/contract-sanitized" --valid-pointers-only > "$work/sanitized.log" 2>&1
printf 'PASS: normal and ASan/UBSan real-wrapper contracts\n'

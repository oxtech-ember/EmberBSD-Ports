#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). This probe executes no target code.
set -eu
[ "$#" = 4 ] || {
    echo 'Usage: probe-header-abi.sh GCC_PREFIX SYSROOT VERIFIED_GST_GOOD_SOURCE NEW_OUTPUT' >&2
    exit 2
}
compiler=$1 sysroot=$2 source=$3 output=$4
for path do
    case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2;; esac
done
[ ! -e "$output" ] && [ ! -L "$output" ] || exit 2
cc=$compiler/bin/aarch64--netbsd-gcc
objcopy=$compiler/bin/aarch64--netbsd-objcopy
[ "$("$cc" -dumpfullversion)" = 16.2.0 ]
[ "$("$cc" -dumpmachine)" = aarch64--netbsd ]
[ -f "$sysroot/usr/include/sys/videoio.h" ]
[ -f "$source/sys/v4l2/ext/videodev2.h" ]
profile=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
mkdir "$output"
"$cc" --version > "$output/compiler.txt"
sha256sum "$profile/tests/header-abi.c" \
    "$sysroot/usr/include/sys/videoio.h" "$source/sys/v4l2/ext/"*.h \
    "$sysroot/usr/pkg/lib/glib-2.0/include/glibconfig.h" > "$output/inputs.sha256"
for mode in native bundled; do
    if [ "$mode" = native ]; then set -- -DNATIVE_VIDEOIO; else set --; fi
    "$cc" --sysroot="$sysroot" -std=c11 -Wall -Wextra -Werror \
        -I"$source/sys/v4l2" \
        -I"$sysroot/usr/pkg/include/glib-2.0" \
        -I"$sysroot/usr/pkg/lib/glib-2.0/include" "$@" \
        -c "$profile/tests/header-abi.c" -o "$output/$mode.o"
    "$objcopy" -O binary -j .rodata "$output/$mode.o" "$output/$mode.bin"
done
[ -s "$output/native.bin" ]
cmp "$output/native.bin" "$output/bundled.bin"
sha256sum "$output/native.bin" "$output/bundled.bin" > "$output/outputs.sha256"
echo 'PASS: selected AArch64 V4L2 structure sizes, member offsets and ioctl numbers match'

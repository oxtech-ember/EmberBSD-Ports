#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Focused compile diagnostic, not a package.
set -eu
[ "$#" = 4 ] || {
    echo 'Usage: ffmpeg-cross.sh VERIFIED_PATCHED_SOURCE TARGET_CC HOST_CC NEW_OUTPUT' >&2
    exit 2
}
source=$1 target_cc=$2 host_cc=$3 output=$4
for path do
    case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./+-]*) echo 'Use simple paths.' >&2; exit 2;; esac
done
[ ! -e "$output" ] && [ ! -L "$output" ] || exit 2
[ "$("$target_cc" -dumpfullversion)" = 16.2.0 ]
[ "$("$target_cc" -dumpmachine)" = aarch64--netbsd ]
[ "$("$host_cc" -dumpfullversion)" = 16.2.0 ]
[ "$("$host_cc" -dumpmachine)" != aarch64--netbsd ]
[ -f "$source/libavcodec/v4l2_compat.h" ]
profile=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
# Select the real target ABI. Do not fabricate constants for an old sysroot.
"$target_cc" -std=c11 -Werror -x c -fsyntax-only - <<'CHECK'
#include <sys/types.h>
#include <sys/videoio.h>
#ifndef V4L2_PIX_FMT_HEVC
#error The target sysroot must export the native HEVC format
#endif
int main(void) { return V4L2_PIX_FMT_HEVC == 0; }
CHECK
mkdir "$output"
mkdir "$output/tmp"
export TMPDIR="$output/tmp"
sha256sum "$source/configure" "$source/libavcodec/"v4l2*.[ch] \
    "$profile/ffmpeg-no-device.c" "$profile/ffmpeg-semaphore.c" "$target_cc" "$host_cc" > "$output/inputs.sha256"
"$target_cc" --version > "$output/target-compiler.txt"
"$host_cc" --version > "$output/host-compiler.txt"
ar=$("$target_cc" -print-prog-name=ar)
nm=$("$target_cc" -print-prog-name=nm)
ranlib=$("$target_cc" -print-prog-name=ranlib)
(
    cd "$output"
    "$source/configure" --arch=aarch64 --target-os=netbsd \
        --enable-cross-compile --cc="$target_cc" --host-cc="$host_cc" \
        --host-ld="$host_cc" --ar="$ar" --nm="$nm" --ranlib="$ranlib" \
        --disable-autodetect --disable-everything --disable-doc \
        --disable-programs --disable-debug --enable-static --disable-shared \
        --enable-v4l2-m2m --enable-decoder=hevc_v4l2m2m \
        --enable-encoder=hevc_v4l2m2m > configure.log 2>&1
)
grep -q '^#define HAVE_SYS_VIDEOIO_H 1$' "$output/config.h"
! grep -q '^#define HAVE_LINUX_VIDEODEV2_H 1$' "$output/config.h"
grep -q '^#define CONFIG_HEVC_V4L2M2M_DECODER 1$' "$output/config_components.h"
grep -q '^#define CONFIG_HEVC_V4L2M2M_ENCODER 1$' "$output/config_components.h"
grep -q '^#define CONFIG_HEVC_DECODER 0$' "$output/config_components.h"
"${GMAKE:-make}" -C "$output" -j "${JOBS:-2}" V=1 \
    libavcodec/libavcodec.a libavutil/libavutil.a > "$output/build.log" 2>&1
"$target_cc" -std=c11 -Wall -Wextra -Werror -I"$source" -I"$output" \
    "$profile/ffmpeg-no-device.c" "$output/libavcodec/libavcodec.a" \
    "$output/libavutil/libavutil.a" -lm -lpthread -o "$output/ffmpeg-no-device"
"$target_cc" -std=c11 -Wall -Wextra -Werror -I"$source" -I"$output" \
    "$profile/ffmpeg-semaphore.c" "$output/libavcodec/libavcodec.a" \
    "$output/libavutil/libavutil.a" -Wl,--wrap=sem_init,--wrap=sem_destroy \
    -lm -lpthread -o "$output/ffmpeg-semaphore"
sha256sum "$output/ffmpeg-no-device" "$output/ffmpeg-semaphore" "$output/libavcodec/libavcodec.a" \
    "$output/libavutil/libavutil.a" > "$output/outputs.sha256"
echo 'PASS: native-header HEVC stateful M2M build; target execution remains separate'

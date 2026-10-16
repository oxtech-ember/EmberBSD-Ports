#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Focused upstream V4L2 plugin diagnostic.
set -eu
[ "$#" = 5 ] || {
    echo 'Usage: gstreamer-cross.sh VERIFIED_PATCHED_GOOD_SOURCE MESON_SOURCE CROSS_FILE TARGET_CC NEW_OUTPUT' >&2
    exit 2
}
source=$1 meson=$2 crossfile=$3 target_cc=$4 output=$5
for path do
    case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2;; esac
done
[ ! -e "$output" ] && [ ! -L "$output" ] || exit 2
[ "$("$target_cc" -dumpfullversion)" = 16.2.0 ]
[ "$("$target_cc" -dumpmachine)" = aarch64--netbsd ]
[ "$(python3 "$meson/meson.py" --version)" = 1.12.1 ]
: "${CC_FOR_BUILD:?Select the native GCC16 compiler}"
: "${CXX_FOR_BUILD:?Select the native GCC16 C++ compiler}"
[ "$("$CC_FOR_BUILD" -dumpfullversion)" = 16.2.0 ]
[ "$("$CXX_FOR_BUILD" -dumpfullversion)" = 16.2.0 ]
mkdir "$output"
sha256sum "$crossfile" "$source/meson.build" "$source/sys/v4l2/meson.build" \
    "$source/sys/v4l2/"*.[ch] "$source/sys/v4l2/ext/"*.h > "$output/inputs.sha256"
python3 "$meson/meson.py" setup "$output/build" "$source" \
    --prefix=/usr/pkg --libdir=lib --cross-file="$crossfile" \
    --wrap-mode=nodownload -Dauto_features=disabled -Dv4l2=enabled \
    -Dv4l2-libv4l2=disabled -Dv4l2-gudev=disabled -Dtests=disabled \
    -Dexamples=disabled -Dnls=disabled -Ddoc=disabled -Dorc=disabled \
    > "$output/configure.log" 2>&1
# Check the compiler which Meson actually selected, not only an input variable.
ruby -rjson -e '
    compilers = JSON.parse(File.read(ARGV[0])).fetch("host").fetch("c")
    abort "Unexpected target compiler" unless compilers.fetch("version") == "16.2.0" && compilers.fetch("exelist") == [ARGV[1]]
' "$output/build/meson-info/intro-compilers.json" "$target_cc"
"${NINJA:-ninja}" -C "$output/build" -v > "$output/build.log" 2>&1
python3 "$meson/meson.py" install -C "$output/build" \
    --destdir="$output/stage" --no-rebuild > "$output/install.log" 2>&1
plugin=$output/stage/usr/pkg/lib/gstreamer-1.0/libgstvideo4linux2.so
[ -s "$plugin" ]
sha256sum "$plugin" > "$output/outputs.sha256"
echo 'PASS: actual upstream V4L2 plugin cross-build; hardware factories require real M2M discovery'

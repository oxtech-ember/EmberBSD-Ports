#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Bounded installed plugin scenarios, no hardware I/O.
set -eu
[ "$#" = 4 ] || { echo 'Usage: gstreamer-plugins-runtime.sh VIDEO_FIXTURES FFMPEG_RESULTS GI_CHECKER NEW_OUTPUT' >&2; exit 2; }
video=$(CDPATH= cd -- "$1" && pwd)
ffmpeg=$(CDPATH= cd -- "$2" && pwd)
checker=$(CDPATH= cd -- "$(dirname -- "$3")" && pwd)/$(basename -- "$3")
umask 077
mkdir "$4"
work=$(CDPATH= cd -- "$4" && pwd)
PATH=/usr/pkg/bin:/usr/pkg/sbin:/usr/sbin:/usr/bin:/bin:/sbin; export PATH
unset LD_LIBRARY_PATH LD_PRELOAD GI_TYPELIB_PATH GST_PLUGIN_PATH GST_PLUGIN_PATH_1_0
GST_REGISTRY=$work/registry.bin; export GST_REGISTRY
sysctl kern.boottime > "$work/boot.before"
"$checker" > "$work/introspection.log" 2>&1
pkg_info -e gst-plugins1-base > "$work/packages.txt"
pkg_info -e gst-plugins1-bad >> "$work/packages.txt"
run() { timeout -k 5 60 gst-launch-1.0 -e "$@"; }
run filesrc location="$video/frames.yuv" blocksize=6144 ! \
    rawvideoparse format=i420 width=64 height=64 framerate=24/1 ! \
    videoconvert ! videoscale ! video/x-raw,format=I420,width=64,height=64 ! \
    filesink location="$work/converted.yuv" > "$work/convert.log" 2>&1
cmp "$video/frames.yuv" "$work/converted.yuv"
# Exercise the bad family's real H.264/H.265 parsers and independently decode.
for codec in h264 hevc; do
    case "$codec" in h264) name=libx264; parser=h264parse; caps=video/x-h264,stream-format=byte-stream,alignment=au ;; hevc) name=libx265; parser=h265parse; caps=video/x-h265,stream-format=byte-stream,alignment=au ;; esac
    timeout -k 5 60 ffmpeg9 -nostdin -v error -i "$ffmpeg/$name.mkv" \
        -c:v copy -bsf:v "${codec}_mp4toannexb" -f "$codec" "$work/input.$codec"
    run filesrc location="$work/input.$codec" ! "$parser" ! "$caps" ! \
        filesink location="$work/parsed.$codec" > "$work/$parser.log" 2>&1
    timeout -k 5 60 ffmpeg9 -nostdin -v error -i "$work/parsed.$codec" \
        -pix_fmt yuv420p -f rawvideo "$work/$codec.yuv"
    cmp "$video/frames.yuv" "$work/$codec.yuv"
done
run audiotestsrc num-buffers=12 wave=sine ! audioconvert ! audioresample ! \
    audio/x-raw,rate=48000,channels=2 ! fakesink > "$work/audio.log" 2>&1
result=0
run filesrc location="$work/absent.input" ! fakesink > "$work/invalid.log" 2>&1 || result=$?
[ "$result" != 0 ] && [ "$result" != 124 ] && [ "$result" != 137 ]
pkg_admin check gst-plugins1-base gst-plugins1-bad > "$work/package-check.txt"
sysctl kern.boottime > "$work/boot.after"
cmp "$work/boot.before" "$work/boot.after"
echo 'PASS: 20 typelibs, video conversion, H.264/H.265 parser pixels, audio pipeline and missing input'

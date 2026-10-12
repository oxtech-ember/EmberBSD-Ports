#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Installed software codec and filter scenarios.
set -eu
[ "$#" = 3 ] || { echo "Usage: $0 AUDIO_FIXTURES VIDEO_FIXTURES NEW_OUTPUT" >&2; exit 2; }
audio=$(CDPATH= cd -- "$1" && pwd)
video=$(CDPATH= cd -- "$2" && pwd)
umask 077
mkdir "$3"
work=$(CDPATH= cd -- "$3" && pwd)
PATH=/usr/pkg/bin:/usr/sbin:/usr/bin:/bin:/sbin; export PATH
LC_ALL=C.UTF-8; export LC_ALL
unset LD_LIBRARY_PATH LD_PRELOAD AOM_SIMD_CAPS AOM_SIMD_CAPS_MASK VPX_SIMD_CAPS VPX_SIMD_CAPS_MASK
ulimit -c 0
sysctl kern.boottime > "$work/boot.before"
pkg_info -e ffmpeg9 > "$work/package.txt"
ffmpeg9 -version > "$work/version.txt"
ffmpeg9 -encoders > "$work/encoders.txt" 2>&1
ffmpeg9 -decoders > "$work/decoders.txt" 2>&1
ffmpeg9 -filters > "$work/filters.txt" 2>&1
ldd /usr/pkg/bin/ffmpeg9 > "$work/ffmpeg.ldd"
! grep -q 'not found' "$work/ffmpeg.ldd"
run() { timeout -k 5 180 ffmpeg9 -nostdin -hide_banner -v error "$@"; }
# Lossless byte comparisons exercise installed external H.264/H.265/AV1/VP9 libraries.
for codec in libx264 libx265 libaom-av1 libvpx-vp9; do
    case "$codec" in
        libx264) set -- -preset ultrafast -qp 0 ;;
        libx265) set -- -preset ultrafast -x265-params lossless=1:pools=1:frame-threads=1 ;;
        libaom-av1) set -- -cpu-used 8 -crf 0 -b:v 0 ;;
        libvpx-vp9) set -- -deadline realtime -cpu-used 8 -lossless 1 ;;
    esac
    run -f rawvideo -pixel_format yuv420p -video_size 64x64 -framerate 24 \
        -i "$video/frames.yuv" -frames:v 4 -an -c:v "$codec" -threads 2 "$@" \
        "$work/$codec.mkv" > "$work/$codec-encode.log" 2>&1
    run -i "$work/$codec.mkv" -pix_fmt yuv420p -f rawvideo "$work/$codec.yuv" \
        > "$work/$codec-decode.log" 2>&1
    cmp "$video/frames.yuv" "$work/$codec.yuv"
    ffprobe9 -v error -count_frames -select_streams v:0 \
        -show_entries stream=width,height,nb_read_frames -of default=nw=1 \
        "$work/$codec.mkv" > "$work/$codec-probe.txt"
    grep -qx 'width=64' "$work/$codec-probe.txt"
    grep -qx 'height=64' "$work/$codec-probe.txt"
    grep -qx 'nb_read_frames=4' "$work/$codec-probe.txt"
done
# The repaired dispatch must also retain the independent scalar code paths.
for codec in libaom-av1 libvpx-vp9; do
    case "$codec" in
        libaom-av1) set -- -cpu-used 8 -crf 0 -b:v 0 ;;
        libvpx-vp9) set -- -deadline realtime -cpu-used 8 -lossless 1 ;;
    esac
    AOM_SIMD_CAPS_MASK=0 VPX_SIMD_CAPS_MASK=0 run -f rawvideo \
        -pixel_format yuv420p -video_size 64x64 -framerate 24 \
        -i "$video/frames.yuv" -frames:v 4 -an -c:v "$codec" -threads 2 "$@" \
        "$work/$codec-scalar.mkv" > "$work/$codec-scalar-encode.log" 2>&1
    AOM_SIMD_CAPS_MASK=0 VPX_SIMD_CAPS_MASK=0 run -c:v "$codec" \
        -i "$work/$codec-scalar.mkv" -pix_fmt yuv420p -f rawvideo \
        "$work/$codec-scalar.yuv" > "$work/$codec-scalar-decode.log" 2>&1
    cmp "$video/frames.yuv" "$work/$codec-scalar.yuv"
done

# This format stays compatible with lame-fixtures.rb's independent PCM checker.
run -i "$audio/tone.wav" -c:a libmp3lame -b:a 192k \
    -metadata title='Title café 東京' "$work/audio.mp3" > "$work/mp3-encode.log" 2>&1
run -i "$work/audio.mp3" -c:a pcm_s16le "$work/audio.wav" > "$work/mp3-decode.log" 2>&1
ffprobe9 -v error -show_entries format_tags=title -of default=nw=1:nk=1 \
    "$work/audio.mp3" > "$work/audio-title.txt"
printf '%s\n' 'Title café 東京' > "$work/expected-title.txt"
cmp "$work/expected-title.txt" "$work/audio-title.txt"
run -i "$audio/tone.wav" -c:a libopus "$work/audio.ogg" > "$work/opus-encode.log" 2>&1
run -i "$work/audio.ogg" -ar 44100 -c:a pcm_s16le "$work/opus.wav" > "$work/opus-decode.log" 2>&1
# Two inverse flips return the original pixels through the production filter graph.
run -f rawvideo -pixel_format yuv420p -video_size 64x64 -i "$video/frames.yuv" \
    -vf hflip,hflip -f rawvideo "$work/filtered.yuv" > "$work/filter.log" 2>&1
cmp "$video/frames.yuv" "$work/filtered.yuv"
printf '%s\n' 'not a media file' > "$work/invalid.input"
result=0
run -i "$work/invalid.input" -f null - > "$work/invalid.log" 2>&1 || result=$?
[ "$result" != 0 ] && [ "$result" != 124 ] && [ "$result" != 137 ]
sysctl kern.boottime > "$work/boot.after"
cmp "$work/boot.before" "$work/boot.after"
echo 'PASS: four lossless video codecs, MP3/Opus, Unicode metadata, inverse filters and malformed input'

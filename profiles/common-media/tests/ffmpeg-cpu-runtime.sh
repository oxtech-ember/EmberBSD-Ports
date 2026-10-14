#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Bounded built-in CPU file-codec checks.
set -eu
[ "$#" = 3 ] || { echo 'Usage: ffmpeg-cpu-runtime.sh AUDIO_FIXTURES VIDEO_FIXTURES NEW_OUTPUT' >&2; exit 2; }
audio=$1 video=$2 out=$3
for path do case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2;; esac; done
[ ! -e "$out" ] && [ ! -L "$out" ] || { echo 'Output path already exists.' >&2; exit 2; }
[ -f "$audio/tone.wav" ] && [ -f "$audio/tone.pcm" ] && [ -f "$video/frames.yuv" ] || exit 1
umask 022
mkdir "$out"
ffmpeg=${FFMPEG:-ffmpeg9}
ffprobe=${FFPROBE:-ffprobe9}
LC_ALL=C; export LC_ALL
unset LD_LIBRARY_PATH LD_PRELOAD
"$ffmpeg" -version > "$out/version.txt"
run() { "$ffmpeg" -nostdin -hide_banner -v error -filter_threads 1 -filter_complex_threads 1 "$@"; }
run -f rawvideo -pixel_format yuv420p -video_size 64x64 -framerate 24 \
    -i "$video/frames.yuv" -frames:v 4 -an -c:v ffv1 -level 3 -g 1 -slicecrc 1 -threads 2 \
    "$out/video.mkv" > "$out/video-encode.log" 2>&1
run -xerror -err_detect explode -i "$out/video.mkv" -pix_fmt yuv420p -f rawvideo \
    "$out/decoded.yuv" > "$out/video-decode.log" 2>&1
cmp "$video/frames.yuv" "$out/decoded.yuv"
"$ffprobe" -v error -count_frames -select_streams v:0 \
    -show_entries stream=codec_name,width,height,nb_read_frames -of default=nw=1 \
    "$out/video.mkv" > "$out/video-probe.txt"
grep -qx 'codec_name=ffv1' "$out/video-probe.txt"
grep -qx 'width=64' "$out/video-probe.txt"
grep -qx 'height=64' "$out/video-probe.txt"
grep -qx 'nb_read_frames=4' "$out/video-probe.txt"
"$ffprobe" -v error -select_streams v:0 -show_entries frame=best_effort_timestamp_time \
    -of csv=p=0 "$out/video.mkv" > "$out/timestamps.txt"
printf '%s\n' 0.000000 0.042000 0.083000 0.125000 > "$out/expected-timestamps.txt"
cmp "$out/expected-timestamps.txt" "$out/timestamps.txt"
run -f rawvideo -pixel_format yuv420p -video_size 64x64 -framerate 24 \
    -i "$video/frames.yuv" -vf hflip,hflip -f rawvideo "$out/filtered.yuv" \
    > "$out/filter.log" 2>&1
cmp "$video/frames.yuv" "$out/filtered.yuv"
run -i "$audio/tone.wav" -c:a pcm_s16le "$out/audio.wav" > "$out/audio-encode.log" 2>&1
run -i "$out/audio.wav" -c:a pcm_s16le -f s16le "$out/audio.pcm" > "$out/audio-decode.log" 2>&1
cmp "$audio/tone.pcm" "$out/audio.pcm"
"$ffprobe" -v error -show_entries stream=codec_name,sample_rate,channels,duration \
    -of default=nw=1 "$out/audio.wav" > "$out/audio-probe.txt"
grep -qx 'codec_name=pcm_s16le' "$out/audio-probe.txt"
grep -qx 'sample_rate=44100' "$out/audio-probe.txt"
grep -qx 'channels=1' "$out/audio-probe.txt"
grep -qx 'duration=1.000000' "$out/audio-probe.txt"
printf 'not a media file\n' > "$out/invalid.input"
head -c 64 "$out/video.mkv" > "$out/truncated.mkv"
for file in invalid.input truncated.mkv; do
    status=0
    run -xerror -err_detect explode -i "$out/$file" -f null - > "$out/$file.log" 2>&1 || status=$?
    # FFmpeg 9 returns the low byte of AVERROR_INVALIDDATA or AVERROR(EIO).
    # Require these codec errors; a signal or instrumentation error must fail.
    case "$file:$status" in invalid.input:183|truncated.mkv:251) ;; *) exit 1;; esac
    printf '%s\n' "$status" > "$out/$file.status"
done
echo 'PASS: exact FFV1 pixels, four frame timestamps, inverse filters, PCM samples and two damaged-input failures'

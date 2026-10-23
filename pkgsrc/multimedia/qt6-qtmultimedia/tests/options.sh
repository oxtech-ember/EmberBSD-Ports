#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Evaluate the production recipe option selector.
set -eu
[ "$#" = 1 ] || { echo "Usage: $0 NEW_OUTPUT" >&2; exit 2; }
out=$1
case "$out" in /*) ;; *) echo 'Absolute output path required' >&2; exit 2 ;; esac
tests=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
recipe=${tests%/tests}
: "${BMAKE:=bmake}"
mkdir "$out"
fixture=$out/pkgsrc
mkdir -p "$fixture/mk" "$fixture/multimedia/qt6-qtmultimedia" \
    "$fixture/multimedia/ffmpeg9" "$fixture/multimedia/gst-plugins1-base" \
    "$fixture/multimedia/gst-plugins1-bad" "$fixture/audio/pulseaudio"
cp "$recipe/options.mk" "$fixture/multimedia/qt6-qtmultimedia/options.mk"
: > "$fixture/mk/bsd.fast.prefs.mk"
printf '%s\n' 'PKG_OPTIONS= ${TEST_OPTIONS}' > "$fixture/mk/bsd.options.mk"
printf '%s\n' 'SELECTED_FFMPEG= yes' 'PKG_BUILD_OPTIONS.ffmpeg9=' > "$fixture/multimedia/ffmpeg9/buildlink3.mk"
printf '%s\n' 'SELECTED_PULSE= yes' > "$fixture/audio/pulseaudio/buildlink3.mk"
printf '%s\n' 'SELECTED_GST_BASE= yes' > "$fixture/multimedia/gst-plugins1-base/buildlink3.mk"
printf '%s\n' 'SELECTED_GST_BAD= yes' > "$fixture/multimedia/gst-plugins1-bad/buildlink3.mk"
cat > "$fixture/multimedia/qt6-qtmultimedia/Makefile" <<'MAKE'
.include "options.mk"
all:
	@printf '%s\n' 'ARGS=${CONFIGURE_ARGS}' 'FFMPEG=${SELECTED_FFMPEG:Uno}' \
	    'PULSE=${SELECTED_PULSE:Uno}' 'GST_BASE=${SELECTED_GST_BASE:Uno}' \
	    'GST_BAD=${SELECTED_GST_BAD:Uno}' 'PLIST_FFMPEG=${PLIST.ffmpeg:Uno}' \
	    'SUGGESTED=${PKG_SUGGESTED_OPTIONS}' 'PLIST_X11=${PLIST.x11:Uno}'
MAKE
field() { sed -n "s/^$1=//p" "$2"; }
fail() { echo "FAIL: $*" >&2; exit 1; }
count=0
for opsys in NetBSD Darwin Linux; do
    for selection in none gstreamer pulseaudio both; do
        case "$selection" in
            none) options=; pulse=no; gst=no ;;
            gstreamer) options=gstreamer; pulse=no; gst=yes ;;
            pulseaudio) options=pulseaudio; pulse=yes; gst=no ;;
            both) options='gstreamer pulseaudio'; pulse=yes; gst=yes ;;
        esac
        raw=$out/$opsys-$selection.txt
        "$BMAKE" -C "$fixture/multimedia/qt6-qtmultimedia" \
            "OPSYS=$opsys" "TEST_OPTIONS=$options" > "$raw"
        case "$opsys:$selection" in
            NetBSD:*|Darwin:*|Linux:pulseaudio|Linux:both) ffmpeg=yes ;;
            *) ffmpeg=no ;;
        esac
        [ "$(field FFMPEG "$raw")" = "$ffmpeg" ] || fail "$opsys/$selection FFmpeg dependency"
        [ "$(field PLIST_FFMPEG "$raw")" = "$ffmpeg" ] || fail "$opsys/$selection FFmpeg manifest"
        [ "$(field PULSE "$raw")" = "$pulse" ] || fail "$opsys/$selection PulseAudio dependency"
        [ "$(field GST_BASE "$raw")" = "$gst" ] || fail "$opsys/$selection GStreamer base dependency"
        [ "$(field GST_BAD "$raw")" = "$gst" ] || fail "$opsys/$selection GStreamer bad dependency"
        if [ "$ffmpeg" = yes ]; then
            case " $(field ARGS "$raw") " in *' -feature-ffmpeg '*) ;; *) fail "$opsys/$selection explicit FFmpeg configuration" ;; esac
        fi
        # Qt 6.12 src/multimedia/qt_cmdline.cmake defines these options.
        # Qt's configure also accepts the generic [-no]-feature-NAME form.
        for arg in $(field ARGS "$raw"); do
            case "$arg" in
                -alsa|-no-alsa|-gstreamer|-no-gstreamer|-pulseaudio|-no-pulseaudio) ;;
                -feature-*|-no-feature-*) ;;
                *) fail "$opsys/$selection unknown Qt configure option $arg" ;;
            esac
        done
        if [ "$opsys" = Darwin ]; then
            [ "$(field PLIST_X11 "$raw")" = no ] || fail 'Darwin X11 selection changed'
        else
            case " $(field SUGGESTED "$raw") " in *' gstreamer pulseaudio '*) ;; *) fail 'Default desktop backends changed' ;; esac
        fi
        count=$((count + 1))
    done
done
printf 'PASS: %s production recipe selections; NetBSD video-only dependency, desktop defaults and other platforms\n' "$count"
echo 'Dependency includes are fixture markers; this does not replace full pkgsrc configuration.'

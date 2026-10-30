#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Run inside an existing Wayland session.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 ABSOLUTE_BINARY NEW_LOG_DIRECTORY" >&2; exit 2; }
binary=$1 logs=$2
case "$binary:$logs" in /*:/*) ;; *) echo 'Absolute paths required' >&2; exit 2;; esac
qpa=${EMBER_QTQUICK_QPA:-wayland}
renderer=${EMBER_QTQUICK_EXPECTED_RENDERER:-V3D }
case "$qpa" in
    wayland) : "${XDG_RUNTIME_DIR:?An existing private Wayland runtime directory is required}"; : "${WAYLAND_DISPLAY:?An existing Wayland display is required}" ;;
    eglfs) : "${EMBER_QTQUICK_KMS_CONFIG:?An absolute EGLFS KMS configuration is required}"; case "$EMBER_QTQUICK_KMS_CONFIG" in /*) ;; *) exit 2;; esac ;;
    *) echo 'Expected wayland or eglfs QPA' >&2; exit 2;;
esac
mkdir "$logs"
run()
{
    platform=$1
    shift
    /usr/bin/timeout -k 5 30 /usr/bin/env -i \
        PATH=/usr/pkg/bin:/usr/bin:/bin HOME="$HOME" \
        XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-}" WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-}" \
        EMBER_QTQUICK_EXPECTED_QPA="$qpa" EMBER_QTQUICK_EXPECTED_RENDERER="$renderer" \
        QT_QPA_EGLFS_KMS_CONFIG="${EMBER_QTQUICK_KMS_CONFIG:-}" \
        QT_QPA_PLATFORM="$platform" QT_WAYLAND_CLIENT_BUFFER_INTEGRATION=wayland-egl \
        QT_WAYLAND_DISABLE_WINDOWDECORATION=1 \
        "$binary" "$@"
}
for name in normal restart; do
    run "$qpa" > "$logs/$name.log" 2>&1
    grep -F "renderer=$renderer" "$logs/$name.log" >/dev/null
    if [ "$qpa" = wayland ]; then result=V3D; else result=EGLFS; fi
    grep -F -x "PASS: Qt Quick $result QML scene/layer pixels and window destruction" "$logs/$name.log" >/dev/null
    awk '/^phase=/ { n++; if ($0 != "phase=" n " scene-pixels=1024 layer-pixels=1024") exit 1 }
        END { if (n != 16) exit 1 }' "$logs/$name.log"
done
status=0
run "$qpa" --wrong-pixel > "$logs/wrong-pixel.log" 2>&1 || status=$?
[ "$status" = 3 ]
grep -q 'FAIL: Qt Quick pixel mismatch' "$logs/wrong-pixel.log"
! grep -q '^PASS:' "$logs/wrong-pixel.log"
status=0
run minimal > "$logs/wrong-platform.log" 2>&1 || status=$?
[ "$status" = 2 ]
grep -q 'FAIL: actual selected QPA required' "$logs/wrong-platform.log"
! grep -q '^PASS:' "$logs/wrong-platform.log"
status=0
run "$qpa" --missing-module > "$logs/missing-module.log" 2>&1 || status=$?
[ "$status" = 2 ]
grep -q 'FAIL: QML module load' "$logs/missing-module.log"
! grep -q '^PASS:' "$logs/missing-module.log"
sed -n 's/^loaded=//p' "$logs/normal.log" | sort -u > "$logs/loaded-paths.txt"
while IFS= read -r library; do
    [ "$library" != "$binary" ] || continue
    case "$library" in /usr/pkg/*|/usr/lib/*|/lib/*|/usr/libexec/ld.elf_so|/libexec/ld.elf_so) ;;
        *) echo "Unexpected loaded path: $library" >&2; exit 1;;
    esac
    /usr/bin/sha256 "$library"
done < "$logs/loaded-paths.txt" > "$logs/loaded-sha256.txt"
/usr/bin/sha256 "$binary" > "$logs/binary-sha256.txt"
echo 'PASS: two Qt Quick GPU processes, scene/layer pixels and input rejection; no scanout claim'

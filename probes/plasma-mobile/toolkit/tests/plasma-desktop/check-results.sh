#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Shared assertions for recorded evidence.
set -eu
[ "$#" -eq 2 ] || [ "$#" -eq 3 ] || exit 2
profile=${3-v3d}
case "$profile" in v3d|powervr-zink) ;; *) exit 2 ;; esac
check_renderer()
{
    # Read renderer values, not environment settings or unrelated log lines.
    awk -v mode="$1" -v profile="$profile" '
        mode == "support" && /^OpenGL renderer string:/ {
            value = $0
            sub(/^OpenGL renderer string:[[:space:]]*/, "", value)
            check(value)
        }
        mode == "renderer" && /^(\[[0-9]+\] )?qt\.rhi\.general: OpenGL VENDOR:/ {
            if ($0 !~ /OpenGL VENDOR: .* RENDERER: .* VERSION:/) {
                bad = 1
                next
            }
            value = $0
            sub(/^.*OpenGL VENDOR: .* RENDERER: /, "", value)
            sub(/ VERSION:.*$/, "", value)
            check(value)
        }
        function check(value, lower) {
            count++
            lower = tolower(value)
            if (lower ~ /llvmpipe|lavapipe|softpipe|qpainter/)
                bad = 1
            if (profile == "v3d" && value !~ /^V3D /)
                bad = 1
            if (profile == "powervr-zink" &&
                (lower !~ /(^|[^[:alnum:]_])zink([^[:alnum:]_]|$)/ ||
                 lower !~ /(^|[^[:alnum:]_])powervr([^[:alnum:]_]|$)/))
                bad = 1
        }
        END { exit (count == 0 || bad) }
    ' "$2"
}
case "$1" in
support)
    grep -qx 'Compositing is active' "$2"
    # KWin 6.8 names its OpenGL compositing backend OpenGL ES.
    grep -Eq '^Compositing Type: OpenGL( ES)?$' "$2"
    if grep '^Compositing Type:' "$2" | grep -Ev '^Compositing Type: OpenGL( ES)?$'; then
        echo 'FAIL: non-OpenGL compositing type' >&2
        exit 1
    fi
    check_renderer support "$2"
    ;;
renderer)
    # Qt 6.12 qrhi.cpp and qrhigles2.cpp emit this with QSG_INFO=1.
    check_renderer renderer "$2"
    if grep -E 'starting invalid corona|Open GL context could not be created|QQmlApplicationEngine failed|Error loading QML file|module .* is not installed|Type .* unavailable|failed to load component|Error loading [Aa]pplet|error when loading applet' "$2"; then
        echo 'FAIL: Plasma reported a QML or rendering initialization error' >&2
        exit 1
    fi
    ;;
png)
    # PNG signature, IHDR, and the requested 320x256 dimensions.
    signature=$(od -An -tx1 -N24 "$2" | tr -d ' \n')
    [ "$signature" = 89504e470d0a1a0a0000000d494844520000014000000100 ]
    ;;
*) exit 2 ;;
esac

#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Shared assertions for recorded evidence.
set -eu
[ "$#" -eq 2 ] || exit 2
case "$1" in
support)
    grep -qx 'Compositing is active' "$2"
    grep -qx 'Compositing Type: OpenGL' "$2"
    grep -q '^OpenGL renderer string:.*V3D ' "$2"
    ;;
renderer)
    # Qt 6.12 qrhi.cpp and qrhigles2.cpp emit this with QSG_INFO=1.
    grep -q 'OpenGL VENDOR: .* RENDERER: V3D .* VERSION:' "$2"
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

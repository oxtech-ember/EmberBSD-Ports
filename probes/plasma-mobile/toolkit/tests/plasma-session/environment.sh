#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). KWin passes the actual display environment.
set -eu
: "${EMBER_PLASMA_OUTPUT:?}"
cd "$EMBER_PLASMA_OUTPUT"
: "${WAYLAND_DISPLAY:?}" "${DISPLAY:?}" "${XAUTHORITY:?}"
printf '%s\n' "$WAYLAND_DISPLAY" "$DISPLAY" "$XAUTHORITY" > display-env.tmp
mv display-env.tmp display-env

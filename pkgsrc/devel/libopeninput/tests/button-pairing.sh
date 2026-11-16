#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Host test of the button pairing rule shipped in
# patches/patch-wscons-unpaired-buttons.  LEGACY=1 builds the previous
# behaviour (red run).  Usage: sh tests/button-pairing.sh [patch-file]
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
patch=${1:-$here/../patches/patch-wscons-unpaired-buttons}
cc=${CC:-cc}
out=$(mktemp -d)
trap 'rm -rf "$out"' EXIT HUP INT TERM
# Lines of the new file between the markers: added ("+") and context (" ").
awk '
    /^\+.*wscons-button-state begin/ { on = 1; next }
    /^\+.*wscons-button-state end/   { on = 0; next }
    on && /^[+ ]/ { print substr($0, 2) }
' "$patch" > "$out/button-state-extract.h"
[ -s "$out/button-state-extract.h" ] || { echo "no button state code in $patch" >&2; exit 1; }
extra=
[ -z "${LEGACY:-}" ] || extra=-DLEGACY
"$cc" -std=c11 -Wall -Wextra -Werror $extra -I"$out" "$here/button-pairing.c" -o "$out/t"
"$out/t"

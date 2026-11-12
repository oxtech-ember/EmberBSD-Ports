#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Host test of the swipe state functions shipped in
# patches/patch-wscons-swipe-gestures.  LEGACY=1 builds the previous behaviour
# (red run).  Usage: sh tests/swipe-state.sh [patch-file]
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
patch=${1:-$here/../patches/patch-wscons-swipe-gestures}
cc=${CC:-cc}
out=$(mktemp -d)
trap 'rm -rf "$out"' EXIT HUP INT TERM
# Added lines between the markers, from every hunk, without the leading "+".
awk '
    /^\+.*wscons-swipe-state begin/ { on = 1; next }
    /^\+.*wscons-swipe-state end/   { on = 0; next }
    on && /^\+/ { print substr($0, 2) }
' "$patch" > "$out/swipe-state-extract.h"
[ -s "$out/swipe-state-extract.h" ] || { echo "no swipe state code in $patch" >&2; exit 1; }
extra=
[ -z "${LEGACY:-}" ] || extra=-DLEGACY
"$cc" -std=c11 -Wall -Wextra -Werror $extra -I"$out" "$here/swipe-state.c" -o "$out/t"
"$out/t"

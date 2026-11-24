#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Host test of wscons_swipe_step_ends() in
# patches/patch-wscons-xy-swipe-frames: the X and Y of one kernel swipe step
# become one libinput update.  Usage: sh tests/swipe-frames.sh [patch-file]
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
patch=${1:-$here/../patches/patch-wscons-xy-swipe-frames}
out=$(mktemp -d)
trap 'rm -rf "$out"' EXIT HUP INT TERM
awk '
    /^\+.*wscons-swipe-frame begin/ { on = 1; next }
    /^\+.*wscons-swipe-frame end/   { on = 0; next }
    on && /^\+/ { print substr($0, 2) }
' "$patch" > "$out/swipe-frame-extract.h"
[ -s "$out/swipe-frame-extract.h" ] || { echo "no swipe frame code in $patch" >&2; exit 1; }
"${CC:-cc}" -std=c11 -Wall -Wextra -Werror -I"$out" "$here/swipe-frames.c" -o "$out/t"
"$out/t"

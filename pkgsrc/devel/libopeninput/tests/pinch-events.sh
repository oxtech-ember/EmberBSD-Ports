#!/bin/sh
# SPDX-License-Identifier: MIT
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
patch=${1:-$here/../patches/patch-wscons-swipe-gestures}
out=$(mktemp -d)
trap 'rm -rf "$out"' EXIT HUP INT TERM
awk '/^\+.*wscons-pinch-bridge begin/ {on=1;next} /^\+.*wscons-pinch-bridge end/ {on=0;next} on && /^\+/ {print substr($0,2)}' "$patch" > "$out/pinch-extract.h"
"${CC:-cc}" -std=c11 -Wall -Wextra -Wno-unused-function -I"$out" "$here/pinch-events.c" -o "$out/test"
"$out/test"

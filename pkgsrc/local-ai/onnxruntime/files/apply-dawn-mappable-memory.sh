#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD contributors (AI-assisted).
# Apply the pinned Dawn change only to its complete expected preimage.
set -eu
root=$1
patch_cmd=$2
patch_file=$3
if "$patch_cmd" -s -f -C -F 0 -r /dev/null -p1 -d "$root" -i "$patch_file" </dev/null >/dev/null 2>&1; then
    "$patch_cmd" -s -f -F 0 -p1 -d "$root" -i "$patch_file" </dev/null
elif "$patch_cmd" -s -f -C -R -F 0 -r /dev/null -p1 -d "$root" -i "$patch_file" </dev/null >/dev/null 2>&1; then
    : # already fully applied
else
    echo 'Dawn mappable memory patch preimage changed or partially applied' >&2
    exit 1
fi

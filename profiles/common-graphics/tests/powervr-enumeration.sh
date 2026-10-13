#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted). No Vulkan runtime replacement.
set -eu
[ "$#" = 2 ] || { echo 'Usage: powervr-enumeration.sh VULKAN_HEADERS NEW_WORK' >&2; exit 2; }
headers=$(CDPATH= cd -- "$1" && pwd)
owner=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
flags='-std=c11 -O1 -g -Wall -Wextra -Werror'
if [ "${SANITIZERS:-no}" = yes ]; then
    flags="$flags -fsanitize=address,undefined -fno-omit-frame-pointer"
fi
${CC:-cc} $flags -I"$headers" -I"$owner/../cross" "$owner/powervr-enumeration.c" -o "$work/check"
"$work/check" > "$work/stdout" 2> "$work/stderr"
cat "$work/stdout"
# A lost matching-node check must be detected by the real consumer fixture.
mkdir "$work/mutant"
sed 's/drm.renderMinor != (int64_t)minor(expected)/false/' "$owner/../cross/powervr-enumerate.c" > "$work/mutant/powervr-enumerate.c"
${CC:-cc} $flags -I"$headers" -I"$work/mutant" "$owner/powervr-enumeration.c" -o "$work/mutant/check"
if "$work/mutant/check" > "$work/mutant/stdout" 2> "$work/mutant/stderr"; then
    echo 'FAIL: removed node identity check escaped the regression' >&2; exit 1
fi
echo 'PASS: causal wrong-render-node acceptance is rejected'

#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
set -eu
if [ "$#" -ne 2 ] || [ -z "${CXX:-}" ]; then
    echo "Usage: CXX=/selected/clang++ sh $0 PATCHED_QRHIVULKAN_CPP NEW_OUTPUT" >&2
    exit 2
fi
source_file=$1
output=$2
test ! -e "$output"
mkdir "$output"
sed -n '/^bool QRhiVulkan::canWriteStaticBufferDirectly(QVkBuffer \*bufD)$/,/^}/p' \
    "$source_file" > "$output/predicate.inc"
test -s "$output/predicate.inc"
"$CXX" -std=c++17 -O2 -Wall -Wextra -Werror -I "$output" \
    "$(dirname "$0")/host-static-uploads.cpp" -o "$output/predicate-test"
"$output/predicate-test"

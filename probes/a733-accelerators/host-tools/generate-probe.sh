#!/bin/sh
# SPDX-License-Identifier: MIT
set -eu
if [ "$#" -ne 6 ]; then
    echo "usage: $0 MESA_SOURCE MESA_BUILD MESA_CLC PCO_CLC SPIRV_VAL OUT" >&2
    exit 2
fi
mesa=$1
build=$2
clc=$3
pco=$4
validator=$5
out=$6
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
mkdir -p "$out"
for name in nop store; do
    "$clc" -o "$out/$name.spv" "$here/cs-probe-$name.cl" -- \
        -I"$mesa/src" -I"$mesa/include" -I"$mesa/src/compiler/libcl" \
        -I"$mesa/src/imagination" -I"$build/src/imagination" \
        -cl-std=cl2.0 -D__OPENCL_VERSION__=200 \
        -DHAVE___BUILTIN_FFS -DHAVE___BUILTIN_CLZ
    "$validator" "$out/$name.spv"
    # no_pred_cf is the upstream uscgen build setting. Keep IR validation on.
    PCO_DEBUG=no_pred_cf PCO_DEBUG_PRINT=cs,internal,nir,binary,verbose,stats \
        "$pco" "$out/$name.spv" "$out/$name.h" "$out/$name.c" \
        bvnc=36.56.104.183 > "$out/$name.stdout" 2> "$out/$name.stderr"
done

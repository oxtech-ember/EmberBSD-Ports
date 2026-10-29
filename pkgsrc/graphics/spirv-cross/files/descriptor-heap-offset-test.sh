#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Validate both supported zero offset forms and reject unrepresentable offsets.
set -eu
[ "$#" = 8 ] || { echo 'Usage: descriptor-heap-offset-test.sh SOURCE GLSLANG CROSS AS DIS VAL PYTHON NEW_WORK' >&2; exit 2; }
src=$1 glslang=$2 cross=$3 as=$4 dis=$5 val=$6 python=$7 work=$8
[ ! -e "$work" ] || { echo 'New work path required' >&2; exit 2; }
mkdir "$work"
shader=$src/shaders-no-opt/vulkan/frag/descriptor-heap.vk.nocompat.spv16.frag
"$glslang" --amb --target-env vulkan1.3 -V -o "$work/input.spv" "$shader" >/dev/null
"$dis" --raw-id "$work/input.spv" -o "$work/input.spvasm"
"$python" - "$work" <<'PY'
from pathlib import Path
import re, sys
p = Path(sys.argv[1]); text = (p / 'input.spvasm').read_text()
def one(pattern):
    values = re.findall(pattern, text, re.M)
    assert len(values) == 1, (pattern, values)
    return values[0]
struct = one(r'^\s*OpName %(\d+) "WriteImages1D_heap"$')
array = one(r'^\s*%' + struct + r' = OpTypeStruct %(\d+)\s*$')
size = one(r'^\s*OpDecorateId %' + array + r' ArrayStrideIdEXT %(\d+)\s*$')
zero = one(r'^\s*OpMemberDecorateIdEXT %' + struct + r' 0 OffsetIdEXT %(\d+)\s*$')
integer = one(r'^\s*%' + zero + r' = OpConstant %(\d+) 0\s*$')
needle = 'OpMemberDecorateIdEXT %' + struct + ' 0 OffsetIdEXT %' + zero
variants = {
    'id-zero': needle,
    'literal-zero': 'OpMemberDecorate %' + struct + ' 0 Offset 0',
    'literal-nonzero': 'OpMemberDecorate %' + struct + ' 0 Offset 16',
    'id-nonzero': 'OpMemberDecorateIdEXT %' + struct + ' 0 OffsetIdEXT %900000',
    'id-spec-zero': 'OpMemberDecorateIdEXT %' + struct + ' 0 OffsetIdEXT %900001',
    'id-sizeof': 'OpMemberDecorateIdEXT %' + struct + ' 0 OffsetIdEXT %' + size,
}
assert text.count(needle) == 1
anchor = '%' + struct + ' = OpTypeStruct %' + array
for name, decoration in variants.items():
    modified = text.replace(needle, decoration)
    if name == 'id-nonzero':
        modified = modified.replace(anchor, '%900000 = OpConstant %' + integer + ' 1\n' + anchor)
    elif name == 'id-spec-zero':
        modified = modified.replace(anchor, '%900001 = OpSpecConstant %' + integer + ' 0\n' + anchor)
    (p / (name + '.spvasm')).write_text(modified)
PY
for mode in id-zero literal-zero literal-nonzero id-nonzero id-spec-zero id-sizeof; do
    "$as" --preserve-numeric-ids --target-env spv1.6 "$work/$mode.spvasm" -o "$work/$mode.spv"
    "$val" --allow-localsizeid --scalar-block-layout --target-env spv1.6 "$work/$mode.spv"
    if "$cross" "$work/$mode.spv" -V --output "$work/$mode.frag" > "$work/$mode.log" 2>&1; then
        case "$mode" in id-zero|literal-zero) ;; *) echo "Unsafe offset accepted: $mode" >&2; exit 1;; esac
        "$glslang" --amb --target-env vulkan1.3 -V -o "$work/$mode-roundtrip.spv" "$work/$mode.frag" >/dev/null
        "$val" --allow-localsizeid --scalar-block-layout --target-env spv1.6 "$work/$mode-roundtrip.spv"
    else
        case "$mode" in id-zero|literal-zero) cat "$work/$mode.log" >&2; exit 1;; esac
        grep -F 'Offset for resource heap must be constant 0.' "$work/$mode.log" >/dev/null
    fi
done
echo 'SPIRV-Cross descriptor heap offset validation PASS'

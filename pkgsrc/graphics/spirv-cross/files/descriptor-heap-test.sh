#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Exercise upstream descriptor heap shader and access qualifiers with real tools.
set -eu
[ "$#" = 6 ] || { echo 'Usage: descriptor-heap-test.sh SOURCE GLSLANG SPIRV_CROSS SPIRV_VAL PYTHON NEW_WORK' >&2; exit 2; }
src=$1 glslang=$2 cross=$3 val=$4 python=$5 work=$6
[ ! -e "$work" ] || { echo 'New work path required' >&2; exit 2; }
mkdir "$work"
shader=$src/shaders-no-opt/vulkan/frag/descriptor-heap.vk.nocompat.spv16.frag
"$glslang" --amb --target-env vulkan1.3 -V -o "$work/in.spv" "$shader" >/dev/null
"$val" --allow-localsizeid --scalar-block-layout --target-env spv1.6 "$work/in.spv"
"$cross" --entry main -V --output "$work/out.frag" "$work/in.spv" --remove-unused-variables
"$glslang" --amb --target-env vulkan1.3 -V -o "$work/out.spv" "$work/out.frag" >/dev/null
"$val" --allow-localsizeid --scalar-block-layout --target-env spv1.6 "$work/out.spv"
"$python" - "$work" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1]); source = (p / 'out.frag').read_text()
write = 'writeonly uniform image1D spvWriteImages1D_heapResourceHeap[];'
read = 'readonly uniform image1D spvRWriteImages1D_heapResourceHeap[];'
assert source.count(write) == source.count(read) == 1
assert 'imageStore(spvWriteImages1D_heapResourceHeap[10]' in source
assert 'imageLoad(spvRWriteImages1D_heapResourceHeap[10]' in source
(p / 'bad-store.frag').write_text(source.replace(write, write.replace('writeonly', 'readonly')))
(p / 'bad-load.frag').write_text(source.replace(read, read.replace('readonly', 'writeonly')))
PY
for mode in store load; do
    if "$glslang" --amb --target-env vulkan1.3 -V -o "$work/bad.spv" "$work/bad-$mode.frag" > "$work/bad-$mode.log" 2>&1; then
        echo "Invalid $mode qualifier accepted" >&2; exit 1
    fi
    case "$mode" in store) qualifier=readonly ;; load) qualifier=writeonly ;; esac
    grep -F "'$qualifier' : argument cannot drop memory qualifier" "$work/bad-$mode.log" >/dev/null
done
echo 'SPIRV-Cross descriptor heap access qualifiers PASS'

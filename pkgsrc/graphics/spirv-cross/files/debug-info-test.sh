#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Regression against upstream golden translations using real glslang debug info.
set -eu
[ "$#" = 5 ] || { echo 'Usage: debug-info-test.sh SOURCE GLSLANG SPIRV_CROSS PYTHON NEW_WORK' >&2; exit 2; }
src=$1 glslang=$2 cross=$3 python=$4 work=$5
[ ! -e "$work" ] || { echo 'New work path required' >&2; exit 2; }
mkdir "$work"
shader=$src/shaders/frag/shader-debug-info-line-directives.line.gV.frag
"$glslang" -V -gV -o "$work/debug102.spv" "$shader" >/dev/null
"$python" - "$work/debug102.spv" "$work/debug100.spv" <<'PY'
from pathlib import Path
import sys
b = Path(sys.argv[1]).read_bytes()
a = b'NonSemantic.Shader.DebugInfo.102'
assert b.count(a) == 1
Path(sys.argv[2]).write_bytes(b.replace(a, b'NonSemantic.Shader.DebugInfo.100'))
PY
for version in 100 102; do
    "$cross" "$work/debug$version.spv" --version 450 --emit-line-directives > "$work/glsl"
    "$cross" "$work/debug$version.spv" --hlsl --shader-model 50 --emit-line-directives > "$work/hlsl"
    "$cross" "$work/debug$version.spv" --msl --emit-line-directives > "$work/msl"
    for mode in glsl hlsl msl; do
        case "$mode" in glsl) directory=shaders ;; hlsl) directory=shaders-hlsl ;; msl) directory=shaders-msl ;; esac
        cmp "$work/$mode" "$src/reference/$directory/frag/shader-debug-info-line-directives.line.gV.frag"
    done
done
echo 'SPIRV-Cross DebugInfo.100/102 golden PASS'

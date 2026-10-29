#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Real QtShaderTools remap fixture. Paths are selected native tools and runtime.
set -eu
[ "$#" = 7 ] || { echo 'Usage: shader-remap.sh FIXTURE TOOL_PREFIX GLSLANG SDK PYTHON VIEW NEW_WORK' >&2; exit 2; }
fixture=$1 tools=$2 glslang=$3 sdk=$4 python=$5 view=$6 work=$7
tests=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
[ ! -e "$work" ] || { echo 'New work path required' >&2; exit 2; }
mkdir "$work"
for version in 1.0 1.6; do
    "$glslang" -V --target-env "spirv$version" -g -o "$work/in.spv" "$tests/shader-remap-unused.vert" >/dev/null
    "$python" "$sdk/scripts/run-darwin-with-runtime.py" --runtime-view "$view" -- "$fixture" "$work/in.spv" "$work/strip.spv" "$work/opt.spv"
    for mode in in strip opt; do
        "$tools/bin/spirv-val" "$work/$mode.spv"
        "$tools/bin/spirv-dis" "$work/$mode.spv" > "$work/$mode.txt"
        grep -F "Version: $version" "$work/$mode.txt" >/dev/null
        grep -F 'OpEntryPoint Vertex' "$work/$mode.txt" >/dev/null
        grep -F 'Location 0' "$work/$mode.txt" >/dev/null
        grep -F 'DescriptorSet 0' "$work/$mode.txt" >/dev/null
        grep -F 'Binding 3' "$work/$mode.txt" >/dev/null
        grep -F 'SpecId 7' "$work/$mode.txt" >/dev/null
        grep -E 'OpSpecConstant .* 1$' "$work/$mode.txt" >/dev/null
    done
done
"$tools/bin/spirv-as" --target-env spv1.6 "$tests/shader-remap-dead.spvasm" -o "$work/dead.spv"
"$python" "$sdk/scripts/run-darwin-with-runtime.py" --runtime-view "$view" -- "$fixture" "$work/dead.spv" "$work/strip.spv" "$work/opt.spv"
for mode in dead strip opt; do
    "$tools/bin/spirv-val" "$work/$mode.spv"
    "$tools/bin/spirv-dis" "$work/$mode.spv" > "$work/$mode.txt"
done
[ "$(grep -c 'OpFunction ' "$work/dead.txt")" = 2 ]
[ "$(grep -c 'OpFunction ' "$work/strip.txt")" = 2 ]
[ "$(grep -c 'OpFunction ' "$work/opt.txt")" = 1 ]
echo 'Qt shader remap validation PASS'

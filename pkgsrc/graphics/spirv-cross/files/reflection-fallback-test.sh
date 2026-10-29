#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# The JSON fallback for an unnamed push constant is derived from its SPIR-V ID.
set -eu
[ "$#" = 6 ] || { echo 'Usage: reflection-fallback-test.sh SOURCE GLSLANG SPIRV_CROSS SPIRV_DIS PYTHON NEW_WORK' >&2; exit 2; }
src=$1 glslang=$2 cross=$3 dis=$4 python=$5 work=$6
[ ! -e "$work" ] || { echo 'New work path required' >&2; exit 2; }
mkdir "$work"
shader=$src/shaders-no-opt/comp/ext-inst-with-forward-refs.gV.vk.nocompat.comp
"$glslang" --amb --target-env vulkan1.1 -V -gV -o "$work/in.spv" "$shader" >/dev/null
"$dis" --raw-id "$work/in.spv" -o "$work/in.dis"
"$cross" "$work/in.spv" --reflect > "$work/reflect.json"
"$cross" "$work/in.spv" --reflect > "$work/reflect-again.json"
cmp "$work/reflect.json" "$work/reflect-again.json"
"$python" - "$work" <<'PY'
from pathlib import Path
import json, re, sys
p = Path(sys.argv[1]); text = (p / 'in.dis').read_text()
ids = re.findall(r'^\s*%(\d+) = OpVariable %\d+ PushConstant\s*$', text, re.M)
assert len(ids) == 1, ids
assert re.search(r'^\s*OpName %' + ids[0] + r' ""\s*$', text, re.M)
reflection = json.loads((p / 'reflect.json').read_text())
assert [item['name'] for item in reflection['push_constants']] == ['_' + ids[0]]
PY
echo 'SPIRV-Cross unnamed resource reflection fallback PASS'

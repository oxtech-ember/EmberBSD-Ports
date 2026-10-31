#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# fluidsynth src/utils/fluid_module.cpp uses std::nothrow. The target libc++
# <string> does not declare it, so the exported recipe must add <new>.
# Compiles the standard includes of the patched file with the target
# compiler; needs no distfile.
# Usage: fluidsynth-module-new.sh TARGET_CXX SYSROOT PREPARED_PKGSRC
set -eu
[ "$#" -eq 3 ] || { echo "Usage: $0 TARGET_CXX SYSROOT PREPARED_PKGSRC" >&2; exit 2; }
cxx=$1 sysroot=$2
tree=$(CDPATH= cd -- "$3" && pwd)
recipe=$tree/audio/fluidsynth
fail() { echo "FAIL: $*" >&2; exit 1; }
scratch=$(mktemp -d "${TMPDIR:-/tmp}/fluidsynth-new.XXXXXX")
trap 'rm -rf "$scratch"' EXIT INT TERM
use='struct ember_module { int x; }; ember_module *ember_new() { return new(std::nothrow) ember_module; }'
compile() { "$cxx" --sysroot="$sysroot" -std=c++17 -fsyntax-only "$1" 2>/dev/null; }
# The premise: with <string> alone the allocation does not compile.
printf '#include <string>\n%s\n' "$use" > "$scratch/premise.cpp"
if compile "$scratch/premise.cpp"; then
    fail 'the target <string> declares std::nothrow; recheck whether the patch is needed'
fi
patch=$recipe/patches/patch-src_utils_fluid__module.cpp
[ -f "$patch" ] || fail 'the fluidsynth recipe has no src/utils/fluid_module.cpp patch'
grep -q '^SHA1 (patch-src_utils_fluid__module.cpp) = ' "$recipe/distinfo" ||
    fail 'distinfo does not record the src/utils/fluid_module.cpp patch'
# The standard includes of the patched file, then the allocation it makes.
awk '/^\+\+\+ src\/utils\/fluid_module.cpp$/ {p=1; next} p && /^[ +]#include </ {print substr($0, 2)}' \
    "$patch" > "$scratch/fluid_module.cpp"
printf '%s\n' "$use" >> "$scratch/fluid_module.cpp"
compile "$scratch/fluid_module.cpp" || fail 'the patched includes do not declare std::nothrow'
echo 'PASS: fluidsynth fluid_module.cpp declares std::nothrow with the target libc++'

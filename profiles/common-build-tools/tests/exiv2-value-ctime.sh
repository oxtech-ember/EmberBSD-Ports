#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# exiv2 src/value.cpp calls std::mktime. The target libc++ <sstream> does not
# declare it, so the exported recipe must add <ctime>. Compiles the standard
# includes of the patched file with the target compiler; needs no distfile.
# Usage: exiv2-value-ctime.sh TARGET_CXX SYSROOT PREPARED_PKGSRC
set -eu
[ "$#" -eq 3 ] || { echo "Usage: $0 TARGET_CXX SYSROOT PREPARED_PKGSRC" >&2; exit 2; }
cxx=$1 sysroot=$2
tree=$(CDPATH= cd -- "$3" && pwd)
recipe=$tree/graphics/exiv2
fail() { echo "FAIL: $*" >&2; exit 1; }
scratch=$(mktemp -d "${TMPDIR:-/tmp}/exiv2-ctime.XXXXXX")
trap 'rm -rf "$scratch"' EXIT INT TERM
use='long ember_mktime() { std::tm t{}; return static_cast<long>(std::mktime(&t)); }'
compile() { "$cxx" --sysroot="$sysroot" -std=gnu++17 -fsyntax-only "$1" 2>/dev/null; }
# The premise: without <ctime> the call does not compile.
printf '#include <sstream>\n%s\n' "$use" > "$scratch/premise.cpp"
if compile "$scratch/premise.cpp"; then
    fail 'the target <sstream> declares std::mktime; recheck whether the patch is needed'
fi
patch=$recipe/patches/patch-src_value.cpp
[ -f "$patch" ] || fail 'the exiv2 recipe has no src/value.cpp patch'
grep -q '^SHA1 (patch-src_value.cpp) = ' "$recipe/distinfo" ||
    fail 'distinfo does not record the src/value.cpp patch'
# The standard includes of the patched file, then the call it makes.
awk '/^\+\+\+ src\/value.cpp$/ {p=1; next} p && /^[ +]#include </ {print substr($0, 2)}' \
    "$patch" > "$scratch/value.cpp"
printf '%s\n' "$use" >> "$scratch/value.cpp"
compile "$scratch/value.cpp" || fail 'the patched includes do not declare std::mktime'
echo 'PASS: exiv2 value.cpp declares std::mktime with the target libc++'

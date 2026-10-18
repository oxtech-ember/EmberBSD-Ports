#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), causal installed llvm-config metadata test.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 PRISTINE_LLVM_PROJECT NEW_WORK" >&2; exit 2; }
source=$1 work=$2
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cmake=${CMAKE:-cmake}
mkdir "$work"
recipe=$root/recipes/lang/llvm
delta=$recipe/patches/patch-tools_llvm-config_CMakeLists.txt
# pkgsrc removes RCS ID lines before it verifies a patch checksum.
expected=$(awk '/^SHA1 \(patch-tools_llvm-config_CMakeLists.txt\)/ {print $4}' "$recipe/distinfo")
actual=$(sed '/[$]NetBSD.*/d' "$delta" | shasum -a 1 | awk '{print $1}')
[ "$expected" = "$actual" ] || { echo 'FAIL: llvm-config patch checksum differs from pkgsrc.' >&2; exit 1; }
mkdir -p "$work/fixed/tools/llvm-config"
flags='-L/private/target-root/usr/pkg/gcc16/lib -Wl,-rpath,/usr/pkg/gcc16/lib -Wl,-rpath-link,/private/target-root/usr/pkg/lib -Wl,-rpath-link,/private/target-root/usr/pkg/gcc16/lib -Wl,-rpath-link,/private/target-root-other/usr/pkg/lib -Wl,-rpath-link,/usr/pkg/lib -L/usr/lib'
reported='-L/usr/pkg/gcc16/lib -Wl,-rpath,/usr/pkg/gcc16/lib -Wl,-rpath-link,/private/target-root-other/usr/pkg/lib -Wl,-rpath-link,/usr/pkg/lib -L/usr/lib'
input=$source/llvm/tools/llvm-config/CMakeLists.txt
cp "$input" "$work/fixed/tools/llvm-config/"
patch -f -N -F 0 -p0 -d "$work/fixed" < \
    "$root/recipes/lang/llvm/patches/patch-tools_llvm-config_CMakeLists.txt" > "$work/patch.log"
if grep -Ei 'offset|fuzz|FAILED' "$work/patch.log"; then exit 1; fi
for variant in baseline fixed; do
    file=$input
    [ "$variant" != fixed ] || file=$work/fixed/tools/llvm-config/CMakeLists.txt
    # Execute the upstream metadata assignment and its patched continuation.
    # The linker flag variable remains observable separately.
    awk '/^set\(LLVM_LDFLAGS / {active=1} /^set\(LLVM_BUILDMODE / {exit} active {print}' \
        "$file" > "$work/$variant.cmake"
    test -s "$work/$variant.cmake"
    for mode in native cross no-sysroot; do
        cross=ON sysroot=/private/target-root
        [ "$mode" != native ] || cross=OFF
        [ "$mode" != no-sysroot ] || sysroot=
        cat > "$work/case.cmake" <<EOF
set(CMAKE_CROSSCOMPILING $cross)
set(CMAKE_SYSROOT "$sysroot")
set(CMAKE_CXX_LINK_FLAGS "$flags")
include("$work/$variant.cmake")
file(WRITE "$work/$variant-$mode.txt" "\${LLVM_LDFLAGS}\n\${CMAKE_CXX_LINK_FLAGS}\n")
EOF
        "$cmake" -P "$work/case.cmake"
        if [ "$variant:$mode" = fixed:cross ]; then
            printf '%s\n%s\n' "$reported" "$flags" > "$work/expected.txt"
        else
            printf '%s\n%s\n' "$flags" "$flags" > "$work/expected.txt"
        fi
        cmp "$work/expected.txt" "$work/$variant-$mode.txt"
    done
done
echo 'PASS: cross metadata drops common build-only rpath-link paths and roots -L; actual build flags, other paths and native/no-sysroot metadata stay intact.'

#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check the runtime fixture paths in testdir.h.
set -eu
[ "$#" = 3 ] || {
    echo "Usage: $0 FCITX_SOURCE FCITX_RECIPE NEW_OUTPUT" >&2
    exit 2
}
: "${CMAKE:?Set an absolute native CMake executable}"
source=$1 recipe=$2 out=$3
for path in "$@" "$CMAKE"; do
    case "$path" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2 ;; esac
done
fail() { echo "FAIL: $*" >&2; exit 1; }
mkdir "$out"
mkdir -p "$out/patched/test" "$out/fixture"
for name in CMakeLists.txt testdir.h.in; do
    cp "$source/test/$name" "$out/patched/test/$name"
    patch -d "$out/patched" -p0 -F0 < "$recipe/patches/patch-test_$name" \
        > "$out/patch-$name.log" 2>&1 || fail "patch $name"
done

# Execute only the actual header-configuration block. The unrelated test
# targets require a complete Fcitx dependency closure and are not stubbed here.
header_block() {
    awk '{ print }
        /^configure_file\(testdir.h.in / { found = 1; exit }
        END { if (!found) exit 1 }' "$1"
}
# Everything from the existing configure_file call onward must stay intact.
build_rules() {
    awk '/^configure_file\(testdir.h.in / { found = 1 }
        found { print }
        END { if (!found) exit 1 }' "$1"
}
build_rules "$source/test/CMakeLists.txt" > "$out/build-rules.before"
build_rules "$out/patched/test/CMakeLists.txt" > "$out/build-rules.after"
cmp "$out/build-rules.before" "$out/build-rules.after" || fail 'test build rules changed'
cat > "$out/fixture/CMakeLists.txt" <<'CMAKE'
cmake_minimum_required(VERSION 3.19)
project(FcitxTestFixturePaths NONE)
include("${CMAKE_CURRENT_SOURCE_DIR}/header-configuration.cmake")
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/build-roots.txt"
    "source=${PROJECT_SOURCE_DIR}\nbinary=${CMAKE_BINARY_DIR}\n")
CMAKE
header_block "$source/test/CMakeLists.txt" > "$out/fixture/header-configuration.cmake"
cp "$source/test/testdir.h.in" "$out/fixture/testdir.h.in"
"$CMAKE" -S "$out/fixture" -B "$out/native" > "$out/native-before.log" 2>&1
cp "$out/native/testdir.h" "$out/native-before.h"
header_value() {
    grep -Fqx "#define $1 \"$2\"" "$3"
}
header_value FCITX5_SOURCE_DIR "$out/fixture" "$out/native-before.h" || fail 'upstream source default'
header_value FCITX5_BINARY_DIR "$out/native" "$out/native-before.h" || fail 'upstream build default'

# These directories need not exist on the build host. Spaces are intentional.
target_source=$out/'target fixtures/source'
target_binary=$out/'target fixtures/build'
configure_cross() {
    "$CMAKE" -S "$out/fixture" -B "$out/cross" \
        -DCMAKE_SYSTEM_NAME=NetBSD \
        "-DFCITX5_TEST_SOURCE_DIR=$target_source" \
        "-DFCITX5_TEST_BINARY_DIR=$target_binary"
}
configure_cross > "$out/cross-before.log" 2>&1
cp "$out/cross/testdir.h" "$out/cross-before.h"
if header_value FCITX5_SOURCE_DIR "$target_source" "$out/cross-before.h" || \
    header_value FCITX5_BINARY_DIR "$target_binary" "$out/cross-before.h"; then
    fail 'baseline already supports the overrides'
fi
echo 'PASS: unpatched header rejects the requested target fixture contract'

header_block "$out/patched/test/CMakeLists.txt" > "$out/fixture/header-configuration.cmake"
cp "$out/patched/test/testdir.h.in" "$out/fixture/testdir.h.in"
"$CMAKE" -S "$out/fixture" -B "$out/native" > "$out/native-after.log" 2>&1
cmp "$out/native-before.h" "$out/native/testdir.h" || fail 'native defaults changed'
configure_cross > "$out/cross-after.log" 2>&1
header_value FCITX5_SOURCE_DIR "$target_source" "$out/cross/testdir.h" || fail 'cross source override missing'
header_value FCITX5_BINARY_DIR "$target_binary" "$out/cross/testdir.h" || fail 'cross build override missing'
grep -Fqx "source=$out/fixture" "$out/cross/build-roots.txt" || fail 'real source root changed'
grep -Fqx "binary=$out/cross" "$out/cross/build-roots.txt" || fail 'real build root changed'
[ ! -e "$target_source" ] && [ ! -e "$target_binary" ] || fail 'configuration wrote into runtime roots'
# Cache values must survive a reconfigure that omits the command-line overrides.
"$CMAKE" -S "$out/fixture" -B "$out/cross" > "$out/cross-cached.log" 2>&1
header_value FCITX5_SOURCE_DIR "$target_source" "$out/cross/testdir.h" || fail 'cached source override lost'
header_value FCITX5_BINARY_DIR "$target_binary" "$out/cross/testdir.h" || fail 'cached build override lost'
echo 'PASS: byte-identical native defaults, cross overrides and cache persistence'

# Validate before set(CACHE PATH). Otherwise CMake converts an untyped
# relative -D value to an absolute host path and hides the invalid input.
for name in SOURCE BINARY; do
    for kind in untyped path empty; do
        case "$kind" in
            untyped) argument="-DFCITX5_TEST_${name}_DIR=relative/fixture" ;;
            path) argument="-DFCITX5_TEST_${name}_DIR:PATH=relative/fixture" ;;
            empty) argument="-DFCITX5_TEST_${name}_DIR:PATH=" ;;
        esac
        log=$out/reject-$name-$kind.log
        if "$CMAKE" -S "$out/fixture" -B "$out/reject-$name-$kind" \
            "$argument" > "$log" 2>&1; then
            fail "$name $kind override accepted"
        fi
        grep -Fq "FCITX5_TEST_${name}_DIR must be an absolute path" "$log" || fail 'unexpected rejection'
    done
done
echo 'PASS: six invalid-path cases rejected; build rules and roots unchanged'
echo 'This configures only the upstream header block. No Fcitx tests were compiled or run.'

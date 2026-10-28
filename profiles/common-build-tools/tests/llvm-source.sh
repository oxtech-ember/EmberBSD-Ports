#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD, AI-assisted LLVM family source/export regressions.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 VERIFIED_DISTFILES NEW_WORK" >&2; exit 2; }
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
distfiles=$(CDPATH= cd -- "$1" && pwd)
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
case "$work:$distfiles" in *[!a-zA-Z0-9_./:-]*) echo 'Use safe absolute paths.' >&2; exit 2 ;; esac
profile=$root/profiles/common-build-tools
recipe_dir() { echo "$root/pkgsrc/$1"; }
archive=llvm-project-23.1.4.src.tar.xz
source=llvm-project-23.1.4.src
verifier=$root/upstream/pkgsrc/mk/checksum/checksum.awk
[ "$(shasum -a 256 "$distfiles/$archive" | awk '{print $1}')" = \
    819ecf7351f1a66f76b2d701d8942faaf5faeb324cb90c9d5b090de142434bb2 ]
# Use the selected SDK checksum producer. Do not replace it with host OpenSSL.
: "${DIGEST:?Set the selected SDK digest executable}"
case "$DIGEST" in /*) ;; *) echo 'DIGEST must be absolute.' >&2; exit 2 ;; esac
[ -x "$DIGEST" ] || { echo 'DIGEST must be executable.' >&2; exit 2; }
export DIGEST
for recipe in lang/llvm lang/clang devel/lld devel/py-llvm-lit; do
    dir=$root/pkgsrc/$recipe
    (cd "$distfiles" && awk -f "$verifier" -- "$dir/distinfo" "$archive")
    [ "$(wc -c < "$distfiles/$archive" | tr -d ' ')" = \
        "$(awk '$1 == "Size" {print $4}' "$dir/distinfo")" ]
    for delta in "$dir"/patches/patch-*; do
        [ -f "$delta" ] || continue
        awk -f "$verifier" -- -p "$dir/distinfo" "$delta"
    done
done
cp "$distfiles/$archive" "$work/$archive"
printf x >> "$work/$archive"
if (cd "$work" && awk -f "$verifier" -- "$root/pkgsrc/lang/llvm/distinfo" "$archive") \
    > "$work/corrupt.log" 2>&1; then exit 1; fi
rm "$work/$archive"
delta=$root/pkgsrc/lang/llvm/patches/patch-cmake_config-ix.cmake
raw=$(shasum -a 1 "$delta" | awk '{print $1}')
sed "s/^SHA1 (patch-cmake_config-ix.cmake) = .*/SHA1 (patch-cmake_config-ix.cmake) = $raw/" \
    "$root/pkgsrc/lang/llvm/distinfo" > "$work/raw-distinfo"
if awk -f "$verifier" -- -p "$work/raw-distinfo" "$delta" > "$work/raw.log" 2>&1; then exit 1; fi
if awk -f "$verifier" -- -p "$root/pkgsrc/lang/llvm/distinfo" \
    "$work/patch-cmake_config-ix.cmake" > "$work/missing.log" 2>&1; then exit 1; fi
# Extract actual targets from the verified archive, not another full monorepo.
mkdir "$work/source"
for project in llvm clang; do
    for delta in "$root/pkgsrc/lang/$project"/patches/patch-*; do
        target=$(awk '/^\+\+\+/ {print $2; exit}' "$delta")
        printf '%s\n' "$source/$project/$target" >> "$work/extract-list"
    done
done
# Include the directly related generation/install declarations for the PLIST gate.
for input in llvm/include/llvm/Analysis/CMakeLists.txt clang/CMakeLists.txt \
    clang/include/clang/Basic/CMakeLists.txt \
    clang/include/clang/Options/CMakeLists.txt clang/include/clang/Sema/CMakeLists.txt \
    llvm/tools/llvm-offload-binary/CMakeLists.txt; do
    printf '%s\n' "$source/$input" >> "$work/extract-list"
done
# All payloads have safe pkgsrc patch paths; decompress the archive once.
tar -xf "$distfiles/$archive" -C "$work/source" -T "$work/extract-list"
for project in llvm clang; do
    for delta in "$root/pkgsrc/lang/$project"/patches/patch-*; do
        patch -f -N -F 0 -p0 -d "$work/source/$source/$project" < "$delta"
    done
done
if patch -f -N -F 0 -p0 -d "$work/source/$source/llvm" < "$delta" \
    > "$work/wrong-project.log" 2>&1; then exit 1; fi
delta=$root/pkgsrc/lang/llvm/patches/patch-cmake_config-ix.cmake
if patch -f -N -F 0 -p0 -d "$work/source/$source/llvm" < "$delta" \
    > "$work/repeat.log" 2>&1; then exit 1; fi
# Explicitly reversed patch payload against pristine must not be accepted.
mkdir "$work/pristine"
tar -xf "$distfiles/$archive" -C "$work/pristine" "$source/llvm/cmake/config-ix.cmake"
diff -u --label cmake/config-ix.cmake.orig --label cmake/config-ix.cmake \
    "$work/source/$source/llvm/cmake/config-ix.cmake" \
    "$work/pristine/$source/llvm/cmake/config-ix.cmake" > "$work/reversed.patch" || [ "$?" = 1 ]
if patch -f -N -F 0 -p0 -d "$work/pristine/$source/llvm" < "$work/reversed.patch" \
    > "$work/reversed-input.log" 2>&1; then exit 1; fi
"$PY" -B "$root/scripts/tests/export-fixture.py" "$root" "$work/pkgsrc" > "$work/export.log"
for recipe in lang/python315 devel/meson lang/llvm lang/clang devel/lld devel/py-llvm-lit; do
    diff -r "$(recipe_dir "$recipe")" "$work/pkgsrc/$recipe"
done
# Accepted Python/Meson recipe bytes and established GCC recipe composition
# are compared without rerunning their native or consumer suites.
# Reuse the production export graph from HEAD. A private patch-name list
# becomes stale when the common GCC provider gains a required patch.
mkdir "$work/reference-ports"
git -C "$root" archive HEAD pkgsrc profiles probes scripts | tar -xf - -C "$work/reference-ports"
mkdir -p "$work/reference-ports/upstream"
ln -s "$root/upstream/pkgsrc" "$work/reference-ports/upstream/pkgsrc"
git -C "$work/reference-ports" init -q
pin=$(git -C "$root/upstream/pkgsrc" rev-parse HEAD)
git -C "$work/reference-ports" update-index --add --cacheinfo "160000,$pin,upstream/pkgsrc"
"$PY" -B "$root/scripts/tests/export-fixture.py" "$work/reference-ports" "$work/reference-pkgsrc" > "$work/reference-export.log"
for recipe in lang/python315 devel/meson lang/gcc16 lang/gcc16-libs lang/gcc16-libjit \
    math/mpfr math/mpcomplex devel/gtexinfo lang/tcl-expect; do
    diff -r "$work/reference-pkgsrc/$recipe" "$work/pkgsrc/$recipe"
done
cmp "$root/profiles/development-toolchain/mk.conf" "$work/pkgsrc/EMBERBSD-DEVELOPMENT-MK.CONF"
if "$PY" -B "$root/scripts/tests/export-fixture.py" "$root" "$work/pkgsrc" > "$work/existing.log" 2>&1; then exit 1; fi
if "$PY" -B "$root/scripts/tests/export-fixture.py" "$root" "$work/unknown" bad > "$work/unknown.log" 2>&1; then exit 1; fi
[ ! -e "$work/unknown" ]
fixture=$work/fixture
mkdir -p "$fixture/scripts" "$fixture/upstream"
cp "$root/scripts/prepare-pkgsrc.sh" "$root/scripts/prepare-pkgsrc.py" "$fixture/scripts/"
for item in profiles probes; do cp -R "$root/$item" "$fixture/$item"; done
# Keep recipe links and their shared patch targets inside the fixture.
cp -R "$root/pkgsrc" "$fixture/pkgsrc"
ln -s "$root/upstream/pkgsrc" "$fixture/upstream/pkgsrc"
git -C "$fixture" init -q
pin=$(git -C "$root/upstream/pkgsrc" rev-parse HEAD)
git -C "$fixture" update-index --add --cacheinfo "160000,$pin,upstream/pkgsrc"
rm "$fixture/pkgsrc/lang/llvm/patches/patch-cmake_config-ix.cmake"
if "$PY" -B "$root/scripts/tests/export-fixture.py" "$fixture" "$work/missing-export" \
    > "$work/missing-export.log" 2>&1; then exit 1; fi
grep -qF 'Missing patch: pkgsrc/lang/llvm/patches/patch-cmake_config-ix.cmake' "$work/missing-export.log"
[ ! -e "$work/missing-export" ]
# These are source/recipe shape contracts, not CMake configure or native tests.
grep -q 'PKG_FAIL_REASON.*not prepared' "$work/pkgsrc/lang/llvm/version.mk"
grep -q -- '-DLLVM_INSTALL_GTEST=ON' "$work/pkgsrc/lang/llvm/options.mk"
grep -q -- '-DLIBCLANG_BUILD_STATIC=ON' "$work/pkgsrc/lang/clang/Makefile.common"
grep -Fq '${FILESDIR}/llvm-runtime-config.sh ${LLVM_CONFIG_PATH:Q}' \
    "$work/pkgsrc/lang/clang/Makefile.common"
grep -q -- '-DLLVM_ENABLE_RTTI=ON' "$work/pkgsrc/lang/llvm/Makefile"
grep -q '^LLVM_LINK_LLVM_DYLIB?= ON' "$work/pkgsrc/lang/llvm/Makefile"
grep -Fq -- '-DLLVM_LINK_LLVM_DYLIB=${LLVM_LINK_LLVM_DYLIB}' "$work/pkgsrc/lang/llvm/Makefile"
! grep -q '^LLVM_EXPERIMENTAL_TARGETS=.*SPIRV' "$work/pkgsrc/lang/llvm/options.mk"
for pair in 'LLVM_ALL_TARGETS LLVM_TARGETS' 'LLVM_ALL_EXPERIMENTAL_TARGETS LLVM_EXPERIMENTAL_TARGETS'; do
    set -- $pair
    awk -v marker="set($1" '$0 == marker {active=1; next}
        active && /^[[:space:]]*\)/ {active=0}
        active {print $1}' "$work/source/$source/llvm/CMakeLists.txt" | LC_ALL=C sort > "$work/upstream-targets"
    awk -v marker="$2=" '$1 == marker {for (i=2; i<=NF; i++) print $i}' \
        "$work/pkgsrc/lang/llvm/options.mk" | LC_ALL=C sort > "$work/profile-targets"
    cmp "$work/upstream-targets" "$work/profile-targets"
done
! grep -q 'lang/libunwind' "$work/pkgsrc/devel/lld/Makefile"
! grep -q '^DISTFILES+=' "$work/pkgsrc/devel/lld/options.mk"
! grep -q '835769' "$work/pkgsrc/devel/lld/distinfo"
grep -q 'lib/libclang.a' "$work/pkgsrc/lang/clang/PLIST"
grep -q 'lib/libLLVMDTLTO.a' "$work/pkgsrc/lang/llvm/PLIST"
! grep -q '^bin/llvm-lit$' "$work/pkgsrc/lang/llvm/PLIST"
sh "$profile/tests/llvm-generated-headers.sh" "$work/source/$source" \
    "$work/pkgsrc" "$work/generated-headers"
echo 'PASS: recipe shape/static payload declarations; native staging/check-files pending'
sh "$profile/tests/llvm-selection.sh" "$work/pkgsrc" "$work/selection"
sh "$profile/tests/clang-runtime-config.sh" "$work/config"
sh "$profile/tests/llvm-lit.sh" "$distfiles/$archive" "$work/lit"
echo 'PASS: LLVM family source/checksum/negative/export contracts; native packages/LLVM23 driver/ELF pending'

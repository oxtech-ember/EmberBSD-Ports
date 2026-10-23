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
# lang/python314 is not exported; all other recipes here are in pkgsrc/.
recipe_dir() {
    if [ "$1" = lang/python314 ]; then echo "$profile/recipes/$1"; else echo "$root/pkgsrc/$1"; fi
}
archive=llvm-project-23.1.3.src.tar.xz
source=llvm-project-23.1.3.src
verifier=$root/upstream/pkgsrc/mk/checksum/checksum.awk
[ "$(shasum -a 256 "$distfiles/$archive" | awk '{print $1}')" = \
    c44186a7762ed28954be72e5ff6df9808e0779d4f1bf014ecc4e7e211d31ee34 ]
cat > "$work/digest" <<'DIGEST'
#!/bin/sh
algorithm=$1; shift
if [ "$#" = 0 ]; then
    [ "$algorithm" = SHA1 ] || exit 2
    shasum -a 1 | awk '{print $1}'; exit
fi
for file do
    case "$algorithm" in
        SHA512) hash=$(shasum -a 512 "$file" | awk '{print $1}') ;;
        BLAKE2s) hash=$("${OPENSSL:-openssl}" dgst -blake2s256 "$file" | awk '{print $NF}') ;;
        *) exit 2 ;;
    esac
    printf '%s (%s) = %s\n' "$algorithm" "$file" "$hash"
done
DIGEST
chmod +x "$work/digest"
export DIGEST=$work/digest
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
sh "$root/scripts/prepare-pkgsrc.sh" "$work/pkgsrc" > "$work/export.log"
for recipe in lang/python314 devel/meson lang/llvm lang/clang devel/lld devel/py-llvm-lit; do
    diff -r "$(recipe_dir "$recipe")" "$work/pkgsrc/$recipe"
done
# Accepted Python/Meson recipe bytes and established GCC recipe composition
# are compared without rerunning their native or consumer suites.
mkdir "$work/reference"
git -C "$root" archive HEAD \
    profiles/common-build-tools/recipes/lang/python314 pkgsrc/devel/meson \
    scripts/prepare-pkgsrc.sh | tar -xf - -C "$work/reference"
for recipe in lang/python314 devel/meson; do
    reference=$(recipe_dir "$recipe")
    diff -r "$work/reference/${reference#"$root"/}" "$work/pkgsrc/$recipe"
done
git -C "$root/upstream/pkgsrc" archive HEAD lang/gcc16 lang/gcc16-libs lang/gcc16-libjit \
    math/mpfr math/mpcomplex devel/gtexinfo lang/tcl-expect mk/pkgformat/pkg/metadata.mk | tar -xf - -C "$work/reference"
for patch in pkgsrc-gcc16.2.patch strict-tests.patch current-prerequisites.patch stable-expect.patch gcc-tsvc-netbsd.patch gcc-modules-fallocate.patch gcc-package-requires.patch; do
    patch -f -N -E -F 0 -p1 -d "$work/reference" < \
        "$root/profiles/development-toolchain/patches/$patch" >> "$work/gcc-reference.log"
done
rm -rf "$work/reference/devel/gtexinfo"
cp -R "$root/pkgsrc/devel/gtexinfo" "$work/reference/devel/gtexinfo"
for recipe in lang/gcc16 lang/gcc16-libs lang/gcc16-libjit math/mpfr math/mpcomplex devel/gtexinfo lang/tcl-expect; do
    diff -r "$work/reference/$recipe" "$work/pkgsrc/$recipe"
done
cmp "$root/profiles/development-toolchain/mk.conf" "$work/pkgsrc/EMBERBSD-DEVELOPMENT-MK.CONF"
if sh "$root/scripts/prepare-pkgsrc.sh" "$work/pkgsrc" > "$work/existing.log" 2>&1; then exit 1; fi
if sh "$root/scripts/prepare-pkgsrc.sh" "$work/unknown" bad > "$work/unknown.log" 2>&1; then exit 1; fi
[ ! -e "$work/unknown" ]
fixture=$work/fixture
mkdir -p "$fixture/scripts" "$fixture/upstream"
cp "$root/scripts/prepare-pkgsrc.sh" "$fixture/scripts/"
for item in profiles probes; do ln -s "$root/$item" "$fixture/$item"; done
# The export rejects links in pkgsrc/, so the fixture gets a private copy.
cp -R "$root/pkgsrc" "$fixture/pkgsrc"
ln -s "$root/upstream/pkgsrc" "$fixture/upstream/pkgsrc"
git -C "$fixture" init -q
pin=$(git -C "$root/upstream/pkgsrc" rev-parse HEAD)
git -C "$fixture" update-index --add --cacheinfo "160000,$pin,upstream/pkgsrc"
rm "$fixture/pkgsrc/lang/llvm/patches/patch-cmake_config-ix.cmake"
if sh "$fixture/scripts/prepare-pkgsrc.sh" "$work/missing-export" \
    > "$work/missing-export.log" 2>&1; then exit 1; fi
grep -qF 'Missing patch: pkgsrc/lang/llvm/patches/patch-cmake_config-ix.cmake' "$work/missing-export.log"
[ ! -e "$work/missing-export" ]
# These are source/recipe shape contracts, not CMake configure or native tests.
grep -q 'PKG_FAIL_REASON.*not prepared' "$work/pkgsrc/lang/llvm/version.mk"
grep -q -- '-DLLVM_INSTALL_GTEST=ON' "$work/pkgsrc/lang/llvm/options.mk"
grep -q -- '-DLIBCLANG_BUILD_STATIC=ON' "$work/pkgsrc/lang/clang/Makefile.common"
grep -q -- '-DLLVM_ENABLE_RTTI=ON' "$work/pkgsrc/lang/llvm/Makefile"
grep -q -- '-DLLVM_LINK_LLVM_DYLIB=ON' "$work/pkgsrc/lang/llvm/Makefile"
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
sh "$profile/tests/clang-config.sh" "$root/pkgsrc/lang/clang/files/native-gcc-config.sh" "$work/config"
sh "$profile/tests/llvm-lit.sh" "$distfiles/$archive" "$work/lit"
echo 'PASS: LLVM family source/checksum/negative/export contracts; native packages/LLVM23 driver/ELF pending'

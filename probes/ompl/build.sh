#!/bin/sh
# SPDX-License-Identifier: MIT
set -eu
umask 022
[ "$#" -ge 1 ] && [ "$#" -le 2 ] || { echo 'Usage: build.sh ABS_NEW_WORK [ABS_CACHE]' >&2; exit 2; }
work=$1
: "${EIGEN_PREFIX:?Set EIGEN_PREFIX to the common Eigen 5.0.1 installation}"
BOOST_PREFIX=${BOOST_PREFIX:-/usr/pkg}
for directory in "$@" "$EIGEN_PREFIX" "$BOOST_PREFIX"; do
    case "$directory" in /*) ;; *) echo 'Use absolute paths.' >&2; exit 2 ;; esac
    case "$directory" in *[!a-zA-Z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2 ;; esac
done
[ ! -e "$work" ] && [ ! -L "$work" ] || { echo 'Work path already exists.' >&2; exit 2; }
case "$(uname -s):$(uname -p)" in NetBSD:aarch64) ;; *) echo 'Native NetBSD/aarch64 required.' >&2; exit 2 ;; esac
CC=${CC:-/usr/pkg/gcc16/bin/gcc}
CXX=${CXX:-/usr/pkg/gcc16/bin/g++}
export CC CXX
[ "$("$CC" -dumpfullversion)" = 16.2.0 ]
[ "$("$CXX" -dumpfullversion)" = 16.2.0 ]
jobs=${JOBS:-1}
for value in "$jobs"; do
    case "$value" in ''|*[!0-9]*) echo 'Limits must be positive integers.' >&2; exit 2 ;; esac
    [ "$value" -gt 0 ] 2>/dev/null || exit 2
done
if [ "${BUILD_AS_KIB+x}" = x ]; then
    case "$BUILD_AS_KIB" in ''|*[!0-9]*) echo 'BUILD_AS_KIB must be positive.' >&2; exit 2 ;; esac
    [ "$BUILD_AS_KIB" -gt 0 ] 2>/dev/null || exit 2
    ulimit -S -v "$BUILD_AS_KIB"
fi
recipe=$(CDPATH= cd "$(dirname "$0")" && pwd)
cmake=${CMAKE:-cmake}
for tool in "$cmake" ninja tar sha256 sha1 patch; do command -v "$tool" >/dev/null; done
mkdir "$work"
mkdir "$work/src" "$work/archives" "$work/logs"
while read -r name expected url; do
    if [ "$#" = 2 ]; then cp "$2/$name" "$work/archives/$name";
    else curl -fLsS --connect-timeout 20 --max-time 900 "$url" -o "$work/archives/$name"; fi
    actual=$(sha256 -q "$work/archives/$name")
    [ "$actual" = "$expected" ] || { echo "Checksum mismatch: $name" >&2; exit 2; }
    printf '%s %s %s\n' "$name" "$actual" "$url" >> "$work/logs/sources.txt"
done < "$recipe/sources.tsv"
while read -r name expected url; do tar -mxf "$work/archives/$name" -C "$work/src"; done < "$recipe/sources.tsv"
package_recipe=$recipe/../../pkgsrc/local-robotics/ompl
patch_file=$package_recipe/patches/patch-pkgconfig
expected=$(awk '$1 == "SHA1" && $2 == "(patch-pkgconfig)" {print $4}' "$package_recipe/distinfo")
actual=$(sed '/[$]NetBSD.*/d' "$patch_file" | sha1 -q)
[ -n "$expected" ] && [ "$actual" = "$expected" ] || { echo 'Patch checksum mismatch.' >&2; exit 2; }
patch -f -F0 -p0 -d "$work/src/ompl-2.0.2" < "$patch_file" > "$work/logs/patch.log" 2>&1
printf '%s\n' "$EIGEN_PREFIX" > "$work/eigen-prefix.txt"
printf '%s\n' "$BOOST_PREFIX" > "$work/boost-prefix.txt"
{ uname -a; "${CXX:-c++}" --version; "$cmake" --version; ninja --version;
  printf 'EIGEN_PREFIX=%s\nBOOST_PREFIX=%s\nJOBS=%s\nBUILD_AS_KIB=%s\n' \
    "$EIGEN_PREFIX" "$BOOST_PREFIX" "$jobs" "${BUILD_AS_KIB:-inherited}";
} > "$work/logs/tools.txt"
run()
{
    stage=$1; shift
    status=0
    "$@" > "$work/logs/$stage.log" 2>&1 || status=$?
    if [ "$status" -ne 0 ]; then tail -60 "$work/logs/$stage.log" >&2; exit "$status"; fi
}
prefix=$work/install
run configure "$cmake" -S "$work/src/ompl-2.0.2" -B "$work/build" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$prefix" -DCMAKE_INSTALL_LIBDIR=lib \
    -DCMAKE_PREFIX_PATH="$EIGEN_PREFIX;$BOOST_PREFIX" -DCMAKE_FIND_USE_PACKAGE_REGISTRY=OFF \
    -DCMAKE_PROJECT_ompl_INCLUDE="$recipe/dependencies.cmake" \
    -DEIGEN_PREFIX="$EIGEN_PREFIX" -DBOOST_PREFIX="$BOOST_PREFIX" \
    -DOMPL_BUILD_SHARED=ON -DOMPL_VERSIONED_INSTALL=OFF -DOMPL_BUILD_TESTS=OFF \
    -DOMPL_BUILD_DEMOS=OFF -DOMPL_BUILD_PYTHON_BINDINGS=OFF -DOMPL_BUILD_VAMP=OFF \
    -DVAMP_BUILD_PYTHON_BINDINGS=OFF -DCMAKE_DISABLE_FIND_PACKAGE_Python=ON \
    -DCMAKE_DISABLE_FIND_PACKAGE_Triangle=ON -DCMAKE_DISABLE_FIND_PACKAGE_flann=ON \
    -DCMAKE_DISABLE_FIND_PACKAGE_spot=ON -DCMAKE_DISABLE_FIND_PACKAGE_yaml-cpp=ON \
    -DCMAKE_DISABLE_FIND_PACKAGE_Doxygen=ON -DFETCHCONTENT_FULLY_DISCONNECTED=ON \
    -DFETCHCONTENT_UPDATES_DISCONNECTED=ON
run build "$cmake" --build "$work/build" --parallel "$jobs"
run install "$cmake" --install "$work/build"
mkdir -p "$prefix/share/ember-ompl/licenses"
cp "$recipe/sources.tsv" "$recipe/PROVENANCE.md" "$prefix/share/ember-ompl/"
cp "$work/src/ompl-2.0.2/LICENSE" "$prefix/share/ember-ompl/licenses/OMPL-BSD-3-Clause"
echo "Installed in $prefix; run test.sh next."

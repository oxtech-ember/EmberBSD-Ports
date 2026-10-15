#!/bin/sh
# SPDX-License-Identifier: MIT
# A disposable native source probe, not a package or system installer.
set -eu
umask 022
[ "$#" -ge 1 ] && [ "$#" -le 2 ] || { echo 'Usage: build.sh ABS_NEW_WORK [ABS_ARCHIVE_CACHE]' >&2; exit 2; }
work=$1
case "$work" in /*) ;; *) echo 'Use an absolute work path.' >&2; exit 2 ;; esac
case "$work" in *[!a-zA-Z0-9_./-]*) echo 'Use a simple work path.' >&2; exit 2 ;; esac
[ ! -e "$work" ] && [ ! -L "$work" ] || { echo 'Work path already exists.' >&2; exit 2; }
if [ "$#" = 2 ]; then
    case "$2" in /*) ;; *) echo 'Use an absolute archive cache.' >&2; exit 2 ;; esac
    [ -d "$2" ] || { echo 'Archive cache is not a directory.' >&2; exit 2; }
fi
jobs=${JOBS:-1}
case "$jobs" in ''|0|*[!0-9]*) echo 'JOBS must be positive.' >&2; exit 2 ;; esac
[ "$jobs" -gt 0 ] 2>/dev/null || { echo 'JOBS must be positive.' >&2; exit 2; }
build_as=${BUILD_AS_KIB:-}
if [ "${BUILD_AS_KIB+x}" = x ]; then
    case "$build_as" in ''|0|*[!0-9]*) echo 'BUILD_AS_KIB must be positive.' >&2; exit 2 ;; esac
    [ "$build_as" -gt 0 ] 2>/dev/null || { echo 'BUILD_AS_KIB must be positive.' >&2; exit 2; }
fi
recipe=$(CDPATH= cd "$(dirname "$0")" && pwd)
mkdir "$work"
mkdir "$work/src" "$work/archives" "$work/logs"
prefix=$work/install
hash()
{
    if command -v sha256 >/dev/null 2>&1; then sha256 -q "$1";
    else shasum -a 256 "$1" | awk '{print $1}'; fi
}
# Check all archives before extracting any, including cached archives.
while read -r name expected url; do
    if [ "$#" = 2 ]; then
        cp "$2/$name" "$work/archives/$name"
    else
        curl -fLsS --connect-timeout 20 --max-time 900 "$url" -o "$work/archives/$name"
    fi
    actual=$(hash "$work/archives/$name")
    [ "$actual" = "$expected" ] || { echo "Checksum mismatch: $name; nothing extracted." >&2; exit 2; }
    printf '%s %s %s\n' "$name" "$actual" "$url" >> "$work/logs/sources.txt"
done < "$recipe/sources.tsv"
[ "$(uname -s)" = NetBSD ] || { echo 'Native EmberBSD/NetBSD required.' >&2; exit 2; }
# Optional user-selected soft limit; preserve the inherited hard limit.
if [ -n "$build_as" ]; then
    ulimit -S -v "$build_as" || { echo 'Could not set the requested address-space limit.' >&2; exit 2; }
    [ "$(ulimit -S -v)" = "$build_as" ] || {
        echo 'Requested address-space limit verification failed.' >&2; exit 2;
    }
fi
CC=${CC:-/usr/pkg/gcc16/bin/gcc}
CXX=${CXX:-/usr/pkg/gcc16/bin/g++}
for tool in "$CC" "$CXX" cmake ninja tar patch; do
    command -v "$tool" >/dev/null || { echo "Missing tool: $tool" >&2; exit 2; }
done
export CC CXX
[ "$("$CC" -dumpfullversion)" = 16.2.0 ] && [ "$("$CXX" -dumpfullversion)" = 16.2.0 ] || {
    echo 'GCC/G++ 16.2.0 required.' >&2; exit 2;
}
printf '%s\n' "$(command -v "$CXX")" > "$work/logs/cxx.txt"
: "${EIGEN_PREFIX:?Set EIGEN_PREFIX to the common Eigen 5.0.1 installation}"
case "$EIGEN_PREFIX" in /*) ;; *) echo 'Use an absolute Eigen prefix.' >&2; exit 2 ;; esac
case "$EIGEN_PREFIX" in *[!a-zA-Z0-9_./-]*) echo 'Use a simple Eigen prefix.' >&2; exit 2 ;; esac
[ -f "$EIGEN_PREFIX/share/eigen3/cmake/Eigen3Config.cmake" ] || {
    echo 'Common Eigen installation is missing.' >&2; exit 2;
}
grep -F 'set(PACKAGE_VERSION "5.0.1")' "$EIGEN_PREFIX/share/eigen3/cmake/Eigen3ConfigVersion.cmake" >/dev/null || {
    echo 'Common Eigen 5.0.1 required.' >&2; exit 2;
}
printf '%s\n' "$EIGEN_PREFIX" > "$work/logs/eigen-prefix.txt"
PKG_CONFIG_PATH=/usr/pkg/lib/pkgconfig:/usr/pkg/share/pkgconfig
export PKG_CONFIG_PATH
for archive in "$work"/archives/*.tar.gz; do tar -xzf "$archive" -C "$work/src"; done
{
    uname -a
    printf 'BUILD_AS_KIB=%s\nJOBS=%s\n' "$(ulimit -v)" "$jobs"
    "$CC" --version
    "$CXX" --version
    cmake --version
    ninja --version
} > "$work/logs/tools.txt"
run()
{
    stage=$1
    shift
    printf '%s\n' "$stage"
    status=0
    "$@" > "$work/logs/$stage.log" 2>&1 || status=$?
    if [ "$status" -ne 0 ]; then
        tail -60 "$work/logs/$stage.log" >&2
        echo "Failed: $stage ($status)" >&2
        exit "$status"
    fi
}
gtsam=$work/src/gtsam-71a25ca36c084cbad1f872e812d6d97fbadfdb05
run gtsam-configure cmake -S "$gtsam" -B "$work/gtsam-build" -G Ninja \
    -C "$recipe/../../pkgsrc/local-robotics/gtsam/features.cmake" \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_STANDARD=17 \
    -DCMAKE_C_COMPILER="$CC" -DCMAKE_CXX_COMPILER="$CXX" \
    -DCMAKE_INSTALL_PREFIX="$prefix" -DCMAKE_INSTALL_LIBDIR=lib \
    -DCMAKE_PREFIX_PATH="$EIGEN_PREFIX;/usr/pkg" \
    -DCMAKE_INSTALL_RPATH="$prefix/lib;/usr/pkg/lib;/usr/pkg/gcc16/lib" \
    -DEigen3_DIR="$EIGEN_PREFIX/share/eigen3/cmake" \
    -DCMAKE_FIND_USE_PACKAGE_REGISTRY=OFF -DCMAKE_FIND_USE_SYSTEM_PACKAGE_REGISTRY=OFF \
    -DCMAKE_EXPORT_NO_PACKAGE_REGISTRY=ON -DBUILD_SHARED_LIBS=ON \
    -DGTSAM_USE_SYSTEM_EIGEN=ON -DGTSAM_USE_SYSTEM_CCOLAMD=OFF \
    -DGTSAM_USE_SYSTEM_SPECTRA=OFF -DGTSAM_SUPPORT_NESTED_DISSECTION=OFF \
    -DGTSAM_USE_BOOST_FEATURES=OFF -DGTSAM_ENABLE_BOOST_SERIALIZATION=OFF \
    -DGTSAM_WITH_TBB=OFF -DGTSAM_WITH_EIGEN_MKL=OFF -DGTSAM_ENABLE_CUDA=OFF \
    -DCMAKE_DISABLE_FIND_PACKAGE_CHOLMOD=ON -DGTSAM_ENABLE_GEOGRAPHICLIB=OFF \
    -DGTSAM_BUILD_TESTS=ON -DGTSAM_BUILD_EXAMPLES_ALWAYS=OFF \
    -DGTSAM_BUILD_TIMING_ALWAYS=OFF -DGTSAM_BUILD_UNSTABLE=OFF \
    -DGTSAM_BUILD_PYTHON=OFF -DGTSAM_INSTALL_MATLAB_TOOLBOX=OFF \
    -DGTSAM_BUILD_WITH_MARCH_NATIVE=OFF -DGTSAM_BUILD_WITH_PRECOMPILED_HEADERS=OFF
run gtsam-build cmake --build "$work/gtsam-build" --target gtsam CppUnitLite --parallel "$jobs"
run gtsam-install cmake --install "$work/gtsam-build"
licenses=$prefix/share/gtsam-probe/licenses
mkdir -p "$licenses/ccolamd" "$licenses/cephes"
cp "$recipe/sources.tsv" "$recipe/PROVENANCE.md" "$prefix/share/gtsam-probe/"
cp "$gtsam/LICENSE" "$gtsam/LICENSE.BSD" "$licenses/"
cp "$gtsam/gtsam/3rdparty/CCOLAMD/Doc/License.txt" "$licenses/ccolamd/"
cp "$gtsam/gtsam/3rdparty/SuiteSparse_config/README.txt" "$licenses/ccolamd/SuiteSparse-README.txt"
cp "$gtsam/gtsam/3rdparty/cephes/LICENSE.txt" "$gtsam/gtsam/3rdparty/cephes/README.md" "$licenses/cephes/"
# The vendored Spectra license is carried in its source headers.
cp "$gtsam/gtsam/3rdparty/Spectra/SymEigsSolver.h" "$licenses/Spectra-SymEigsSolver.h"
cp "$gtsam/gtsam/3rdparty/Eigen/COPYING.MPL2" "$licenses/Spectra-MPL-2.0.txt"
cp "$gtsam/gtsam/3rdparty/cephes/cephes/lanczos.c" "$gtsam/gtsam/3rdparty/cephes/cephes/igami.c" "$licenses/cephes/"
echo "Installed in $prefix; run test.sh to verify the installed consumers."

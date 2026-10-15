#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Build the common Eigen and selected Boost packages.
set -eu
umask 022
[ "$#" = 5 ] || { echo 'Usage: build-dependencies.sh GCC_PREFIX SYSROOT EIGEN_ARCHIVE BOOST_ARCHIVE NEW_OUTPUT' >&2; exit 2; }
compiler=$1 sysroot=$2 eigen_archive=$3 boost_archive=$4 out=$5
for path do
    case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2;; esac
done
[ ! -e "$out" ] && [ ! -L "$out" ] || { echo 'Output path already exists.' >&2; exit 2; }
jobs=${CROSS_JOBS:-4}
case "$jobs" in ''|0|*[!0-9]*) echo 'CROSS_JOBS must be positive.' >&2; exit 2;; esac
[ "$jobs" -gt 0 ] 2>/dev/null || { echo 'CROSS_JOBS must be positive.' >&2; exit 2; }
for language in gcc g++; do
    [ "$("$compiler/bin/aarch64--netbsd-$language" -dumpfullversion)" = 16.2.0 ]
    [ "$("$compiler/bin/aarch64--netbsd-$language" -dumpmachine)" = aarch64--netbsd ]
done
ports=$(CDPATH= cd "$(dirname "$0")/../../.." && pwd -P)
for package in eigen3 boost-headers boost-libs; do
    for name in PLIST DESCR files/SOURCE; do
        [ -f "$ports/pkgsrc/local-robotics/$package/$name" ] || {
            echo "Missing $package package metadata: $name" >&2; exit 2;
        }
    done
done
printf '%s  %s\n' e9c326dc8c05cd1e044c71f30f1b2e34a6161a3b6ecf445d56b53ff1669e3dec "$eigen_archive" | sha256sum -c -
printf '%s  %s\n' 9bed76128d4e46755dbe818487788c6fceb6f72b378f4daa49b7e1e600d9088d "$boost_archive" | sha256sum -c -
[ -f "$sysroot/usr/pkg/gcc16/lib/libstdc++.so.7" ]
mkdir -p "$out/source/eigen" "$out/source/boost" "$out/logs"
tar -xf "$eigen_archive" --strip-components=1 -C "$out/source/eigen"
tar -xf "$boost_archive" --strip-components=1 -C "$out/source/boost"
unset GCC_EXEC_PREFIX COMPILER_PATH LIBRARY_PATH CPATH CPLUS_INCLUDE_PATH C_INCLUDE_PATH
crt=$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0
runtime=$sysroot/usr/pkg/gcc16/lib
headers=$sysroot/usr/pkg/gcc16/include/c++
cat > "$out/toolchain.cmake" <<EOF
set(CMAKE_SYSTEM_NAME NetBSD)
set(CMAKE_SYSTEM_PROCESSOR aarch64)
set(CMAKE_SYSROOT $sysroot)
set(CMAKE_C_COMPILER $compiler/bin/aarch64--netbsd-gcc)
set(CMAKE_CXX_COMPILER $compiler/bin/aarch64--netbsd-g++)
set(CMAKE_C_FLAGS_INIT "-B$crt/ -L$runtime -march=armv8-a")
set(CMAKE_CXX_FLAGS_INIT "-B$crt/ -L$runtime -march=armv8-a -isystem $headers -isystem $headers/aarch64--netbsd -isystem $headers/backward")
set(CMAKE_FIND_ROOT_PATH $sysroot)
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
EOF
run()
{
    name=$1; shift
    status=0
    "$@" > "$out/logs/$name.log" 2>&1 || status=$?
    if [ "$status" -ne 0 ]; then tail -80 "$out/logs/$name.log" >&2; exit "$status"; fi
}
{ "$compiler/bin/aarch64--netbsd-g++" --version; cmake --version; ninja --version; } > "$out/logs/tools.txt"
run eigen-configure cmake -S "$out/source/eigen" -B "$out/eigen-build" -G Ninja \
    -DCMAKE_TOOLCHAIN_FILE="$out/toolchain.cmake" -DCMAKE_INSTALL_PREFIX=/usr/pkg \
    -DCMAKE_INSTALL_LIBDIR=lib -DCMAKE_BUILD_TYPE=Release \
    -DEIGEN_BUILD_TESTING=OFF -DEIGEN_BUILD_DOC=OFF -DEIGEN_BUILD_BLAS=OFF \
    -DEIGEN_BUILD_LAPACK=OFF -DEIGEN_BUILD_DEMOS=OFF
run eigen-install env DESTDIR="$out/eigen-stage" cmake --install "$out/eigen-build"
run boost-configure cmake -S "$out/source/boost" -B "$out/boost-build" -G Ninja \
    -DCMAKE_TOOLCHAIN_FILE="$out/toolchain.cmake" -DCMAKE_INSTALL_PREFIX=/usr/pkg \
    -DCMAKE_INSTALL_LIBDIR=lib -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_STANDARD=17 \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DBUILD_SHARED_LIBS=ON -DBUILD_TESTING=OFF \
    '-DBOOST_INCLUDE_LIBRARIES=serialization;program_options;test' \
    -DBOOST_INSTALL_LAYOUT=system -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON \
    '-DCMAKE_INSTALL_RPATH=/usr/pkg/lib;/usr/pkg/gcc16/lib'
run boost-build cmake --build "$out/boost-build" --parallel "$jobs"
run boost-install env DESTDIR="$out/boost-stage" cmake --install "$out/boost-build"
# Install the complete common header set, including modules that have no
# compiled library in this bounded package profile. Do not vendor private copies.
for directory in "$out/source/boost/libs/"*/include "$out/source/boost/libs/numeric/"*/include; do
    [ -d "$directory/boost" ] && printf '%s\n' "$directory"
done | LC_ALL=C sort > "$out/boost-header-directories.txt"
while IFS= read -r directory; do
    [ -d "$directory/boost" ] || continue
    cp -R "$directory/boost" "$out/boost-stage/usr/pkg/include/"
done < "$out/boost-header-directories.txt"
mkdir -p "$out/boost-headers-stage/usr/pkg/include" "$out/boost-headers-stage/usr/pkg/lib/cmake"
mv "$out/boost-stage/usr/pkg/include/boost" "$out/boost-headers-stage/usr/pkg/include/"
# CMake exports for compiled libraries stay with boost-libs. Header-only
# exports and the Boost umbrella config stay with boost-headers.
for directory in "$out/boost-stage/usr/pkg/lib/cmake/"*; do
    case "$(basename "$directory")" in
        boost_atomic-*|boost_chrono-*|boost_container-*|boost_date_time-*|boost_thread-*|boost_serialization-*|boost_wserialization-*|boost_program_options-*|boost_prg_exec_monitor-*|boost_test_exec_monitor-*|boost_unit_test_framework-*) ;;
        *) mv "$directory" "$out/boost-headers-stage/usr/pkg/lib/cmake/";;
    esac
done
mkdir -p "$out/boost-headers-stage/usr/pkg/share"
mv "$out/boost-stage/usr/pkg/share/boost-1.92.0" "$out/boost-headers-stage/usr/pkg/share/"
mv "$out/boost-stage" "$out/boost-libs-stage"
for package in eigen3 boost-headers boost-libs; do
    case "$package" in
        eigen3) stage=$out/eigen-stage/usr/pkg; source=$out/source/eigen; license=COPYING.MPL2;;
        boost-headers|boost-libs) stage=$out/$package-stage/usr/pkg; source=$out/source/boost; license=LICENSE_1_0.txt;;
    esac
    mkdir -p "$stage/share/licenses/$package"
    cp "$source/$license" "$stage/share/licenses/$package/LICENSE"
    cp "$ports/pkgsrc/local-robotics/$package/files/SOURCE" "$stage/share/licenses/$package/SOURCE"
    if [ "$package" = eigen3 ]; then cp "$source"/COPYING* "$stage/share/licenses/$package/"; fi
    find "$stage" -type f -exec chmod 644 {} +
    (cd "$stage" && find . \( -type f -o -type l \) -print | sed 's|^\./||' | LC_ALL=C sort) > "$out/$package-files.txt"
    sed '/^@comment/d' "$ports/pkgsrc/local-robotics/$package/PLIST" | LC_ALL=C sort > "$out/$package-expected.txt"
    cmp "$out/$package-files.txt" "$out/$package-expected.txt"
done
find "$out/boost-libs-stage/usr/pkg/lib" -type f -name '*.so*' -exec \
    "$compiler/bin/aarch64--netbsd-readelf" -h -d {} + > "$out/elf.txt"
for path in "$compiler" "$sysroot" "$out"; do
    if sed -n '/RPATH\|RUNPATH\|NEEDED/p' "$out/elf.txt" | grep -F "$path"; then
        echo 'Build-host path leaked into target linkage.' >&2; exit 1
    fi
done
echo "Staged Eigen and Boost packages below $out"

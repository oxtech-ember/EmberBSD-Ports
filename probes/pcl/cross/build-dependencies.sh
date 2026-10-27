#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Add current common PCL dependencies to a task sysroot.
# The sysroot must already contain the common devel/boost-libs package.
set -eu
umask 022
[ "$#" = 5 ] || { echo 'Usage: build-dependencies.sh GCC_PREFIX SYSROOT FLANN_ARCHIVE LZ4_ARCHIVE NEW_OUTPUT' >&2; exit 2; }
compiler=$1 sysroot=$2 flann_archive=$3 lz4_archive=$4 out=$5
for path do
    case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) echo 'Use simple absolute paths.' >&2; exit 2;; esac
done
[ ! -e "$out" ] && [ ! -L "$out" ] || { echo 'Output path already exists.' >&2; exit 2; }
jobs=${CROSS_JOBS:-3}
case "$jobs" in ''|*[!0-9]*) echo 'CROSS_JOBS must be positive.' >&2; exit 2;; esac
[ "$jobs" -gt 0 ] 2>/dev/null || { echo 'CROSS_JOBS must be positive.' >&2; exit 2; }
ports=$(CDPATH= cd "$(dirname "$0")/../../.." && pwd -P)
cross=$ports/probes/pcl/cross
for language in gcc g++; do
    [ "$("$compiler/bin/aarch64--netbsd-$language" -dumpfullversion)" = 16.2.0 ]
    [ "$("$compiler/bin/aarch64--netbsd-$language" -dumpmachine)" = aarch64--netbsd ]
done
verify_archive()
{
    name=$1 archive=$2
    expected=$(awk -v name="$name" '$1==name {print $2}' "$cross/dependency-sources.tsv")
    [ "${#expected}" = 64 ] || { echo "Missing source hash: $name" >&2; exit 2; }
    printf '%s  %s\n' "$expected" "$archive" | sha256sum -c -
}
verify_archive flann-1.9.2.tar.gz "$flann_archive"
verify_archive lz4-1.10.0.tar.gz "$lz4_archive"
crt=$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0
runtime=$sysroot/usr/pkg/gcc16/lib
headers=$sysroot/usr/pkg/gcc16/include/c++
[ -f "$crt/crtbeginS.o" ] && [ -f "$runtime/libstdc++.so.7" ]
[ -f "$sysroot/usr/pkg/include/boost/version.hpp" ]
# The common devel/boost-libs package provides Iostreams and Random.
[ -f "$sysroot/usr/pkg/lib/libboost_iostreams.so" ] && [ -f "$sysroot/usr/pkg/lib/libboost_random.so" ]
[ -f "$sysroot/usr/include/zlib.h" ] && [ -f "$sysroot/usr/include/bzlib.h" ] && [ -f "$sysroot/usr/include/lzma.h" ]
recipe()
{
    case $1 in
    lz4) echo "$ports/pkgsrc/archivers/lz4" ;;
    flann) echo "$ports/pkgsrc/math/flann-lib" ;;
    esac
}
unset GCC_EXEC_PREFIX COMPILER_PATH LIBRARY_PATH CPATH CPLUS_INCLUDE_PATH C_INCLUDE_PATH
mkdir -p "$out/source/flann" "$out/source/lz4" "$out/logs"
sha256sum "$flann_archive" "$lz4_archive" "$0" \
    "$cross/import-stage.rb" "$cross/dependency-sources.tsv" > "$out/inputs.sha256"
for package in lz4 flann; do
    recipe=$(recipe "$package")
    sha256sum "$recipe/features.cmake" "$recipe/files/install-stage.sh" "$recipe/files/SOURCE" >> "$out/inputs.sha256"
done
tar -xf "$flann_archive" --strip-components=1 -C "$out/source/flann"
tar -xf "$lz4_archive" --strip-components=1 -C "$out/source/lz4"
for package in lz4 flann; do
    for patch_file in "$(recipe "$package")/patches/"patch-*; do
        [ -f "$patch_file" ] || continue
        sha256sum "$patch_file" >> "$out/inputs.sha256"
        (cd "$out/source/$package" && patch --batch --forward -p0 < "$patch_file") >> "$out/logs/$package-patches.log" 2>&1
    done
done
cat > "$out/toolchain.cmake" <<EOT
set(CMAKE_SYSTEM_NAME NetBSD)
set(CMAKE_SYSTEM_PROCESSOR aarch64)
set(CMAKE_SYSROOT $sysroot)
set(CMAKE_C_COMPILER $compiler/bin/aarch64--netbsd-gcc)
set(CMAKE_CXX_COMPILER $compiler/bin/aarch64--netbsd-g++)
set(CMAKE_C_FLAGS_INIT "-B$crt/ -L$runtime -march=armv8-a -Wl,-rpath,/usr/pkg/gcc16/lib")
set(CMAKE_CXX_FLAGS_INIT "-B$crt/ -L$runtime -march=armv8-a -Wl,-rpath,/usr/pkg/gcc16/lib -isystem $headers -isystem $headers/aarch64--netbsd -isystem $headers/backward")
set(CMAKE_FIND_ROOT_PATH $sysroot)
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
EOT
run()
{
    name=$1; shift
    status=0
    "$@" > "$out/logs/$name.log" 2>&1 || status=$?
    if [ "$status" -ne 0 ]; then tail -80 "$out/logs/$name.log" >&2; exit "$status"; fi
}
configure()
{
    package=$1 source_dir=$2; shift 2
    recipe=$(recipe "$package")
    run "$package-configure" cmake -S "$source_dir" -B "$out/$package-build" -G Ninja \
        -C "$recipe/features.cmake" -DCMAKE_TOOLCHAIN_FILE="$out/toolchain.cmake" \
        -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_STANDARD=17 -DCMAKE_CXX_EXTENSIONS=OFF \
        -DCMAKE_INSTALL_PREFIX=/usr/pkg -DCMAKE_INSTALL_LIBDIR=lib -DCMAKE_INSTALL_MANDIR=man \
        -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON \
        '-DCMAKE_INSTALL_RPATH=/usr/pkg/lib;/usr/pkg/gcc16/lib' "$@"
    run "$package-build" cmake --build "$out/$package-build" --parallel "$jobs"
    run "$package-install" env DESTDIR="$out/$package-stage" cmake --install "$out/$package-build"
    run "$package-stage" sh "$recipe/files/install-stage.sh" "$out/source/$package" "$out/$package-stage/usr/pkg" "$recipe"
}
{ "$compiler/bin/aarch64--netbsd-g++" --version; cmake --version; ninja --version; ruby --version; } > "$out/logs/tools.txt"
configure lz4 "$out/source/lz4/build/cmake"
# FLANN must discover the same staged LZ4 that will be packaged for the target.
run lz4-import ruby "$cross/import-stage.rb" "$out/lz4-stage/usr/pkg" "$sysroot/usr/pkg"
configure flann "$out/source/flann" -DCMAKE_POLICY_VERSION_MINIMUM=3.5
for package in lz4 flann; do
    stage=$out/$package-stage/usr/pkg
    recipe=$(recipe "$package")
    (cd "$stage" && find . \( -type f -o -type l \) -print | sed 's|^\./||' | LC_ALL=C sort) > "$out/$package-files.txt"
    sed '/^@comment/d' "$recipe/PLIST" | LC_ALL=C sort > "$out/$package-expected.txt"
    cmp "$out/$package-files.txt" "$out/$package-expected.txt"
    find "$stage/lib" -type f -name '*.so*' -exec "$compiler/bin/aarch64--netbsd-readelf" -h -d {} + > "$out/$package-elf.txt"
    grep 'Machine:.*AArch64' "$out/$package-elf.txt" >/dev/null
    for path in "$compiler" "$sysroot" "$out"; do
        if sed -n '/RPATH\|RUNPATH\|NEEDED/p' "$out/$package-elf.txt" | grep -F "$path"; then
            echo "Build-host runtime path leaked: $package" >&2; exit 1
        fi
        for metadata in "$stage/lib/cmake" "$stage/lib/pkgconfig"; do
            [ -d "$metadata" ] || continue
            status=0
            grep -r -F "$path" "$metadata" > "$out/logs/$package-metadata-path-check.log" || status=$?
            case "$status" in
                0) cat "$out/logs/$package-metadata-path-check.log" >&2
                   echo "Build-host metadata path leaked: $package" >&2; exit 1;;
                1) ;;
                *) echo "Cannot inspect installed metadata: $package" >&2; exit "$status";;
            esac
        done
    done
done
# Each helper checks the complete input stage before adding any file. Existing
# common packages remain byte-identical; an incompatible collision is fatal.
run flann-import ruby "$cross/import-stage.rb" "$out/flann-stage/usr/pkg" "$sysroot/usr/pkg"
echo "Staged and imported LZ4 and FLANN below $out"

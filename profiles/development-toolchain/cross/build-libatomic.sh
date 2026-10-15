#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted GCC16 runtime component cross-build helper.
set -eu
[ "$#" -eq 4 ] || {
    echo 'Usage: build-libatomic.sh GCC_PREFIX SYSROOT GCC_ARCHIVE NEW_OUTPUT' >&2
    exit 2
}
compiler=$1 sysroot=$2 archive=$3 output=$4
for path in "$@"; do
    case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths without whitespace.' >&2; exit 2;; esac
done
[ ! -e "$output" ] && [ ! -L "$output" ] || {
    echo 'NEW_OUTPUT already exists.' >&2; exit 2;
}
jobs=${CROSS_JOBS:-2}
case "$jobs" in ''|*[!0-9]*) jobs=0;; esac
[ "$jobs" -gt 0 ] 2>/dev/null || { echo 'CROSS_JOBS must be positive.' >&2; exit 2; }
profile=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
recipe=$profile/../../pkgsrc/local-robotics/gcc16-libatomic
cc=$compiler/bin/aarch64--netbsd-gcc
cxx=$compiler/bin/aarch64--netbsd-g++
[ "$("$cc" -dumpfullversion)" = 16.2.0 ]
[ "$("$cxx" -dumpfullversion)" = 16.2.0 ]
[ "$("$cc" -dumpmachine)" = aarch64--netbsd ]
[ "$("$cxx" -dumpmachine)" = aarch64--netbsd ]
crt=$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0
[ -f "$crt/crtbegin.o" ] && [ -f "$sysroot/usr/include/pthread.h" ]
expected=$(awk -F '\t' '$1 == "gcc" && $2 == "16.2.0" { print $4 }' "$profile/sources.tsv")
[ -n "$expected" ] && [ "$(shasum -a 256 "$archive" | awk '{print $1}')" = "$expected" ] || {
    echo 'GCC archive SHA256 mismatch.' >&2; exit 1;
}
mkdir -p "$output"
output=$(CDPATH= cd -- "$output" && pwd -P)
mkdir "$output/source" "$output/build" "$output/logs"
# Extract the runtime and its upstream build auxiliaries. Compiler frontends,
# bundled host prerequisites, and unrelated GCC runtimes are not built.
tar -xf "$archive" --strip-components=1 -C "$output/source" \
    gcc-16.2.0/libatomic gcc-16.2.0/config gcc-16.2.0/include \
    gcc-16.2.0/config.guess gcc-16.2.0/config.sub gcc-16.2.0/ltmain.sh \
    gcc-16.2.0/ltoptions.m4 gcc-16.2.0/ltsugar.m4 gcc-16.2.0/ltversion.m4 \
    'gcc-16.2.0/lt~obsolete.m4' gcc-16.2.0/libtool.m4 gcc-16.2.0/install-sh \
    gcc-16.2.0/missing gcc-16.2.0/depcomp gcc-16.2.0/mkinstalldirs \
    gcc-16.2.0/compile gcc-16.2.0/multilib.am gcc-16.2.0/config-ml.in \
    gcc-16.2.0/gcc/BASE-VER gcc-16.2.0/COPYING3 gcc-16.2.0/COPYING.RUNTIME
unset GCC_EXEC_PREFIX COMPILER_PATH LIBRARY_PATH CPATH CPLUS_INCLUDE_PATH C_INCLUDE_PATH
flags="-O2 -g --sysroot=$sysroot -B$crt/ -L$sysroot/usr/pkg/gcc16/lib -march=armv8-a"
{
    uname -srm
    "$cc" --version
    "$cc" -dumpmachine
    "$compiler/bin/aarch64--netbsd-ld" --version
    make --version
    printf 'sysroot=%s\nCFLAGS=%s\njobs=%s\n' "$sysroot" "$flags" "$jobs"
    shasum -a 256 "$archive" "$cc" "$profile/cross/build-libatomic.sh" "$recipe/files/SOURCE"
} > "$output/inputs.txt"
printf '\n' | "$cc" $flags -dM -E -x c - > "$output/target-macros.txt"
cd "$output/build"
CC="$cc" AR="$compiler/bin/aarch64--netbsd-ar" \
    RANLIB="$compiler/bin/aarch64--netbsd-ranlib" NM="$compiler/bin/aarch64--netbsd-nm" \
    CFLAGS="$flags" LDFLAGS='-Wl,-rpath,/usr/pkg/gcc16/lib' \
    "$output/source/libatomic/configure" \
    --build="$(sh "$output/source/config.guess")" \
    --host=aarch64--netbsd --target=aarch64--netbsd \
    --prefix=/usr/pkg/gcc16 --enable-shared --enable-static --disable-multilib \
    > "$output/logs/configure.log" 2>&1
# The upstream all target copies libraries into a compiler build tree. This
# standalone component uses its public library target and ordinary staged install.
# GCC's bundled Libtool drops unrecognized driver options from CFLAGS during
# linking. Its documented -Wc interface keeps the selected sysroot and startup
# objects in the real compiler invocation. The linker trace records those inputs.
link_flags="-Wc,--sysroot=$sysroot -Wc,-B$crt/ -Wl,-rpath,/usr/pkg/gcc16/lib -Wl,-t"
make -j"$jobs" V=1 LDFLAGS="$link_flags" libatomic.la > "$output/logs/build.log" 2>&1
make DESTDIR="$output/stage" install-toolexeclibLTLIBRARIES > "$output/logs/install.log" 2>&1
# Keep libtool metadata usable on the target. Only the explicitly selected
# sysroot library directory is rewritten to its target location.
from=$(printf '%s' "$sysroot/usr/pkg/gcc16/lib" | sed 's/[.[\*^$\\]/\\&/g')
sed "s|-L$from|-L/usr/pkg/gcc16/lib|g" \
    "$output/stage/usr/pkg/gcc16/lib/libatomic.la" > "$output/libatomic.la"
cat "$output/libatomic.la" > "$output/stage/usr/pkg/gcc16/lib/libatomic.la"
license=$output/stage/usr/pkg/share/licenses/gcc16-libatomic
mkdir -p "$license"
cp "$output/source/COPYING3" "$output/source/COPYING.RUNTIME" "$recipe/files/SOURCE" "$license/"
readelf=$compiler/bin/aarch64--netbsd-readelf
"$readelf" -h "$output/stage/usr/pkg/gcc16/lib/libatomic.so.3.0" > "$output/logs/libatomic-elf.txt"
"$readelf" -d "$output/stage/usr/pkg/gcc16/lib/libatomic.so.3.0" > "$output/logs/libatomic-dynamic.txt"
grep 'Machine:.*AArch64' "$output/logs/libatomic-elf.txt" >/dev/null
grep 'SONAME.*\[libatomic.so.3\]' "$output/logs/libatomic-dynamic.txt" >/dev/null
if grep -E '(RPATH|RUNPATH).*\[.*(/workspace|/tmp|/home|/Users|/usr/local)' "$output/logs/libatomic-dynamic.txt"; then
    echo 'Host directory in target runtime path.' >&2; exit 1
fi
if grep -E '(dependency_libs|libdir)=.*(/workspace|/tmp|/home|/Users)' "$output/stage/usr/pkg/gcc16/lib/libatomic.la"; then
    echo 'Host directory in installed libtool metadata.' >&2; exit 1
fi
cp "$profile/tests/libatomic.cpp" "$output/atomic-contract.cpp"
"$cxx" $flags -std=c++17 -pthread \
    -isystem "$sysroot/usr/pkg/gcc16/include/c++" \
    -isystem "$sysroot/usr/pkg/gcc16/include/c++/aarch64--netbsd" \
    -isystem "$sysroot/usr/pkg/gcc16/include/c++/backward" \
    "$output/atomic-contract.cpp" -L"$output/stage/usr/pkg/gcc16/lib" \
    -Wl,-rpath,/usr/pkg/gcc16/lib -latomic -o "$output/atomic-contract" \
    > "$output/logs/consumer-build.log" 2>&1
"$readelf" -d "$output/atomic-contract" > "$output/logs/consumer-dynamic.txt"
grep 'NEEDED.*\[libatomic.so.3\]' "$output/logs/consumer-dynamic.txt" >/dev/null
(cd "$output/stage/usr/pkg" && find . \( -type f -o -type l \) | sed 's|^./||' | LC_ALL=C sort) > "$output/PLIST"
if [ -f "$recipe/PLIST" ]; then
    sed '/^@comment/d;/^$/d' "$recipe/PLIST" | LC_ALL=C sort > "$output/expected-PLIST"
    cmp "$output/expected-PLIST" "$output/PLIST"
fi
printf 'GCC16 libatomic cross-build PASS: %s\n' "$output/stage"
printf 'Execute atomic-contract on EmberBSD; this build does not claim target runtime acceptance.\n'

#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). GCC16 CPU package with the native FFmpeg delta.
# Run on the build host. HOST_CC/HOST_CXX select native GCC16 executables.
set -eu
umask 022
LC_ALL=C
export LC_ALL
[ "$#" = 4 ] || {
    echo 'Usage: build-ffmpeg-cpu.sh GCC_PREFIX SYSROOT ARCHIVE NEW_OUTPUT' >&2
    exit 2
}
prefix=$1 sysroot=$2 archive=$3 out=$4
for path do
    case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2;; esac
done
[ ! -e "$out" ] && [ ! -L "$out" ]
prefix=$(CDPATH= cd -- "$prefix" && pwd -P)
sysroot=$(CDPATH= cd -- "$sysroot" && pwd -P)
jobs=${CROSS_JOBS:-4}
case "$jobs" in ''|0|*[!0-9]*) echo 'CROSS_JOBS must be positive.' >&2; exit 2;; esac
[ "$jobs" -gt 0 ] 2>/dev/null
profile=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
recipe=$profile/recipes/multimedia/ffmpeg9
for compiler in gcc g++; do
    [ "$("$prefix/bin/aarch64--netbsd-$compiler" -dumpfullversion)" = 16.2.0 ]
    [ "$("$prefix/bin/aarch64--netbsd-$compiler" -dumpmachine)" = aarch64--netbsd ]
done
host_cc=$(command -v "${HOST_CC:-gcc}")
host_cxx=$(command -v "${HOST_CXX:-g++}")
make_tool=$(command -v "${GMAKE:-make}")
patch_tool=$(command -v "${PATCH:-patch}")
pkgconf=$(command -v "${PKG_CONFIG:-pkg-config}")
for tool in "$host_cc" "$host_cxx" "$make_tool" "$patch_tool" "$pkgconf"; do
    case "$tool" in /*) ;; *) echo 'Select an executable tool path.' >&2; exit 2;; esac
    case "$tool" in *[!A-Za-z0-9_./-]*) echo 'Use simple tool paths.' >&2; exit 2;; esac
    [ -x "$tool" ]
done
for compiler in "$host_cc" "$host_cxx"; do
    [ "$("$compiler" -dumpfullversion)" = 16.2.0 ]
    [ "$("$compiler" -dumpmachine)" != aarch64--netbsd ]
done
[ "$("$host_cc" -dumpmachine)" = "$("$host_cxx" -dumpmachine)" ]
for tool in sha256sum sha1sum tar awk sed grep find sort cmp install perl pod2man makeinfo; do
    command -v "$tool" >/dev/null
done
for tool in ar nm ranlib strip readelf; do
    [ -x "$prefix/bin/aarch64--netbsd-$tool" ]
done
crt=$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0
runtime=$sysroot/usr/pkg/gcc16/lib
headers=$sysroot/usr/pkg/gcc16/include/c++
[ -f "$crt/crtbeginS.o" ] && [ -f "$runtime/libgcc_s.so.1" ]
[ -f "$runtime/libstdc++.so.7" ] && [ -d "$headers/aarch64--netbsd" ]
[ -f "$sysroot/usr/include/stdio.h" ]
[ -f "$sysroot/usr/pkg/lib/pkgconfig/libxml-2.0.pc" ]
expected=$(awk '$1 == "multimedia/ffmpeg9" { print $3 }' "$profile/sources.tsv")
[ "${#expected}" = 64 ]
case "$expected" in *[!0-9a-f]*) echo 'Invalid archive hash.' >&2; exit 2;; esac
printf '%s  %s\n' "$expected" "$archive" | sha256sum -c -
# Verify the complete native patch inventory before source preparation.
set -- "$recipe/patches/"patch-*
[ "$#" = 17 ]
for patch_file do
    name=$(basename "$patch_file")
    expected=$(awk -v name="($name)" '$1 == "SHA1" && $2 == name { print $4 }' "$recipe/distinfo")
    actual=$(sed '/[$]NetBSD.*/d' "$patch_file" | sha1sum | awk '{print $1}')
    [ -n "$expected" ] && [ "$expected" = "$actual" ]
done
unset GCC_EXEC_PREFIX COMPILER_PATH LIBRARY_PATH CPATH CPLUS_INCLUDE_PATH C_INCLUDE_PATH
unset CFLAGS CXXFLAGS CPPFLAGS LDFLAGS
mkdir -p "$out/source" "$out/build" "$out/logs" "$out/toolchain" "$out/tmp"
sha256sum "$archive" "$profile/sources.tsv" "$recipe/distinfo" "$recipe/PLIST" \
    "$recipe/Makefile" "$recipe/Makefile.common" "$recipe/options.mk" "$0" \
    "$recipe/patches/"patch-* > "$out/inputs.sha256"
{
    "$prefix/bin/aarch64--netbsd-gcc" --version
    "$prefix/bin/aarch64--netbsd-g++" --version
    "$host_cc" --version
    "$host_cxx" --version
    "$make_tool" --version
    "$pkgconf" --version
} > "$out/tool-versions.txt"
grep -q 'GNU Make' "$out/tool-versions.txt"
tar -xf "$archive" --strip-components=1 -C "$out/source"
for patch_file in "$recipe/patches/"patch-*; do
    name=$(basename "$patch_file")
    "$patch_tool" -f -F0 -p0 -d "$out/source" < "$patch_file" \
        > "$out/logs/$name.log" 2>&1
done
cat > "$out/toolchain/cc" <<EOF
#!/bin/sh
set -eu
exec "$prefix/bin/aarch64--netbsd-gcc" --sysroot="$sysroot" \
    -B"$crt/" -L"$runtime" -Wl,-rpath,/usr/pkg/gcc16/lib "\$@"
EOF
cat > "$out/toolchain/cxx" <<EOF
#!/bin/sh
set -eu
exec "$prefix/bin/aarch64--netbsd-g++" --sysroot="$sysroot" \
    -B"$crt/" -L"$runtime" -Wl,-rpath,/usr/pkg/gcc16/lib \
    -isystem "$headers" -isystem "$headers/aarch64--netbsd" \
    -isystem "$headers/backward" "\$@"
EOF
cat > "$out/toolchain/pkg-config" <<EOF
#!/bin/sh
set -eu
PKG_CONFIG_SYSROOT_DIR="$sysroot"
PKG_CONFIG_LIBDIR="$sysroot/usr/pkg/lib/pkgconfig:$sysroot/usr/lib/pkgconfig"
PKG_CONFIG_PATH=
export PKG_CONFIG_SYSROOT_DIR PKG_CONFIG_LIBDIR PKG_CONFIG_PATH
exec "$pkgconf" "\$@"
EOF
chmod 755 "$out/toolchain/cc" "$out/toolchain/cxx" "$out/toolchain/pkg-config"
export TMPDIR="$out/tmp"
(
    cd "$out/build"
    "$out/source/configure" --prefix=/usr/pkg --arch=aarch64 --target-os=netbsd \
        --enable-cross-compile --cc="$out/toolchain/cc" --cxx="$out/toolchain/cxx" \
        --ar="$prefix/bin/aarch64--netbsd-ar" --nm="$prefix/bin/aarch64--netbsd-nm" \
        --ranlib="$prefix/bin/aarch64--netbsd-ranlib" --strip="$prefix/bin/aarch64--netbsd-strip" \
        --host-cc="$host_cc" --host-ld="$host_cc" --pkg-config="$out/toolchain/pkg-config" \
        --enable-shared --enable-static --enable-pic --enable-gpl --enable-version3 \
        --enable-avfilter --enable-pthreads --enable-runtime-cpudetect \
        --disable-autodetect --disable-ffplay --enable-libxml2 --enable-openssl \
        --enable-zlib --enable-bzlib --enable-lzma --disable-debug --disable-stripping \
        --disable-htmlpages --enable-doc --progs-suffix=9 \
        --incdir=/usr/pkg/include/ffmpeg9 --libdir=/usr/pkg/lib/ffmpeg9 \
        --shlibdir=/usr/pkg/lib/ffmpeg9 --datadir=/usr/pkg/share/ffmpeg9 \
        --docdir=/usr/pkg/share/doc/ffmpeg9 --mandir=/usr/pkg/man \
        --extra-cflags="--sysroot=$sysroot -I$sysroot/usr/pkg/include" \
        --extra-ldflags="--sysroot=$sysroot -L$sysroot/usr/pkg/lib -Wl,-rpath,/usr/pkg/lib -Wl,-rpath,/usr/pkg/lib/ffmpeg9 -Wl,-rpath,/usr/pkg/gcc16/lib"
) > "$out/logs/configure.log" 2>&1
"$make_tool" -C "$out/build" -j "$jobs" V=1 > "$out/logs/build.log" 2>&1
"$make_tool" -C "$out/build" "DESTDIR=$out/stage" install > "$out/logs/install.log" 2>&1
stage=$out/stage/usr/pkg
mkdir -p "$stage/share/doc/ffmpeg9"
install -m 644 "$out/source/doc/"*.txt "$stage/share/doc/ffmpeg9/"
# pkg-config expands dependency -L paths during configure. Ship target paths
# in Libs.private so the static development interfaces also work after install.
mkdir -p "$out/pkgconfig-original"
for pc in "$stage/lib/ffmpeg9/pkgconfig/"*.pc; do
    name=$(basename "$pc")
    cp "$pc" "$out/pkgconfig-original/$name"
    awk -v root="$sysroot" '
        {
            rest = $0
            line = ""
            while ((position = index(rest, root "/")) != 0) {
                line = line substr(rest, 1, position - 1)
                rest = substr(rest, position + length(root))
            }
            print line rest
        }
    ' "$pc" > "$out/tmp/$name"
    install -m 644 "$out/tmp/$name" "$pc"
done
for path in "$sysroot" "$out"; do
    if grep -F "$path" "$stage/lib/ffmpeg9/pkgconfig/"*.pc; then
        echo 'Build-host path leaked into pkg-config metadata.' >&2; exit 1
    fi
done
(
    cd "$stage"
    find . \( -type f -o -type l \) -print | sed 's|^\./||' | LC_ALL=C sort
) > "$out/files.txt"
awk '
    /^@comment/ || /^\$\{PLIST.doc\}/ { next }
    /\$\{/ { bad = 1; next }
    { print }
    END { if (bad) exit 1 }
' "$recipe/PLIST" > "$out/expected-files.unsorted"
LC_ALL=C sort "$out/expected-files.unsorted" > "$out/expected-files.txt"
cmp "$out/files.txt" "$out/expected-files.txt"
set -- "$stage/bin/ffmpeg9" "$stage/bin/ffprobe9"
for library in "$stage/lib/ffmpeg9/"lib*.so.*; do
    [ -f "$library" ] && [ ! -L "$library" ] || continue
    set -- "$@" "$library"
done
[ "$#" = 9 ]
"$prefix/bin/aarch64--netbsd-readelf" -h -l -d "$@" > "$out/elf.txt"
[ "$(grep -c 'Machine:.*AArch64' "$out/elf.txt")" = 9 ]
awk '
    /\(RPATH\)|\(RUNPATH\)|\(NEEDED\)/ {
        value = $0
        sub(/^.*\[/, "", value)
        sub(/\].*$/, "", value)
        if (/\(NEEDED\)/) {
            if (value ~ /\//) { print "Library path leaked into NEEDED: " value; bad = 1 }
        } else {
            count = split(value, paths, ":")
            for (i = 1; i <= count; i++) {
                if (paths[i] != "/usr/pkg/lib" && paths[i] != "/usr/pkg/lib/ffmpeg9" &&
                    paths[i] != "/usr/pkg/gcc16/lib") {
                    print "Unexpected runtime search path: " paths[i]
                    bad = 1
                }
            }
        }
    }
    END { if (bad) exit 1 }
' "$out/elf.txt"
(
    cd "$stage"
    find . -type f -exec sha256sum {} +
) > "$out/artifacts.unsorted.sha256"
LC_ALL=C sort "$out/artifacts.unsorted.sha256" > "$out/artifacts.sha256"
echo "Staged FFmpeg CPU package: $stage; run target acceptance on EmberBSD."

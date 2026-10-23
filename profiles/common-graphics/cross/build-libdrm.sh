#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted cross-build of the canonical libdrm sources.
set -eu
[ "$#" -eq 5 ] || {
    echo 'Usage: build-libdrm.sh ORIGINAL_ARCHIVE CROSS_PREFIX SYSROOT PREPARED_MESON NEW_WORK' >&2
    exit 2
}
archive=$1 prefix=$2 sysroot=$3 meson=$4 work=$5
for path in "$@"; do
    case "$path" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths' >&2; exit 2;; esac
done
[ ! -e "$work" ] && [ ! -L "$work" ] || { echo 'Work already exists' >&2; exit 2; }
profile=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
recipe=$profile/../../pkgsrc/x11/libdrm
python=${PYTHON:-python3.15}
cc=$prefix/bin/aarch64--netbsd-gcc
unset GCC_EXEC_PREFIX COMPILER_PATH LIBRARY_PATH CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH
[ "$("$cc" -dumpmachine)" = aarch64--netbsd ]
[ "$("$cc" -dumpfullversion)" = 16.2.0 ]
[ "$("$python" --version)" = 'Python 3.14.8' ]
[ "$("$python" "$meson/meson.py" --version)" = 1.12.1 ]
for file in usr/include/sys/atomic.h usr/lib/libpci.so usr/lib/crt0.o \
    usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0/crtbegin.o; do
    [ -f "$sysroot/$file" ] || { echo "Missing sysroot input: $file" >&2; exit 1; }
done
hash() {
    if command -v sha256 >/dev/null 2>&1; then sha256 -q "$1";
    else shasum -a 256 "$1" | awk '{print $1}'; fi
}
expected=$(awk -F '\t' '$1=="x11/libdrm" {print $3}' "$profile/sources.tsv")
[ "$(hash "$archive")" = "$expected" ] || { echo 'Archive SHA256 mismatch' >&2; exit 1; }
mkdir "$work"
mkdir "$work/src" "$work/tests"
tar -xJf "$archive" -C "$work/src" --strip-components=1
awk '/^SHA1 / {gsub(/[()]/,"",$2); print $2, $4}' "$recipe/distinfo" |
while read -r name expected_patch; do
    actual=$(sed '/[$]NetBSD.*/d' "$recipe/patches/$name" | shasum -a 1 | awk '{print $1}')
    [ "$actual" = "$expected_patch" ] || { echo "Patch checksum mismatch: $name" >&2; exit 1; }
    patch -f -N -F0 -p0 -d "$work/src" < "$recipe/patches/$name"
done > "$work/patch.log" 2>&1
# The canonical recipe selects NetBSD sys/atomic.h, not libatomic_ops.
sed 's/@ATOMIC_OPS_CHECK@/1/g' "$work/src/xf86drm.h" > "$work/xf86drm.h"
mv "$work/xf86drm.h" "$work/src/xf86drm.h"
cat > "$work/cross.ini" <<EOF
[binaries]
c = '$cc'
ar = '$prefix/bin/aarch64--netbsd-ar'
strip = '$prefix/bin/aarch64--netbsd-strip'
nm = '$prefix/bin/aarch64--netbsd-nm'
# Core-only libdrm uses compiler atomics and no external pkg-config dependency.
pkg-config = '/usr/bin/false'
[host_machine]
system = 'netbsd'
cpu_family = 'aarch64'
cpu = 'aarch64'
endian = 'little'
[properties]
needs_exe_wrapper = true
sys_root = '$sysroot'
[built-in options]
c_args = ['--sysroot=$sysroot', '-B$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0/', '-Werror', '-Wno-error=cpp']
c_link_args = ['--sysroot=$sysroot', '-B$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0/', '-L$sysroot/usr/pkg/gcc16/lib', '-Wl,-rpath,/usr/pkg/gcc16/lib', '-lpci']
EOF
python=$(command -v "$python")
cat > "$work/native.ini" <<EOF
[binaries]
python = '$python'
nm = '$prefix/bin/aarch64--netbsd-nm'
EOF
set --
for module in intel radeon amdgpu nouveau vmwgfx omap exynos freedreno tegra vc4 etnaviv; do
    set -- "$@" "-D$module=disabled"
done
"$python" "$meson/meson.py" setup "$work/build" "$work/src" \
    --cross-file="$work/cross.ini" --native-file="$work/native.ini" \
    --prefix=/usr/pkg --libdir=lib --buildtype=release --wrap-mode=nofallback \
    "$@" -Dman-pages=disabled -Dcairo-tests=disabled -Dvalgrind=disabled \
    -Dtests=true -Dinstall-test-programs=false -Db_lto=false -Dwerror=true \
    > "$work/configure.log" 2>&1
"$python" "$meson/meson.py" compile -C "$work/build" -j "${JOBS:-4}" > "$work/build.log" 2>&1
DESTDIR="$work/stage" "$python" "$meson/meson.py" install -C "$work/build" --no-rebuild > "$work/install.log" 2>&1
sed '/^@/d; /^$/d' "$recipe/PLIST" | LC_ALL=C sort > "$work/expected-files"
(cd "$work/stage/usr/pkg"; find . \( -type f -o -type l \) -print) |
    sed 's,^./,,' | LC_ALL=C sort > "$work/actual-files"
diff -u "$work/expected-files" "$work/actual-files" > "$work/plist.diff"
"$prefix/bin/aarch64--netbsd-readelf" -h -d "$work/stage/usr/pkg/lib/libdrm.so.2.134.0" > "$work/elf.txt"
if grep -E 'RPATH|RUNPATH|NEEDED' "$work/elf.txt" | grep -F -e "$work" -e "$prefix" -e "$sysroot"; then
    echo 'Build path leaked into ELF dependencies' >&2; exit 1
fi
for program in hash drmsl drmdevice; do cp "$work/build/tests/$program" "$work/tests/"; done
cp "$work/src/symbols-check.py" "$work/src/core-symbols.txt" "$work/tests/"
cp "$work/stage/usr/pkg/lib/libdrm.so.2.134.0" "$work/tests/"
ln -s libdrm.so.2.134.0 "$work/tests/libdrm.so.2"
cp "$profile/cross/run-libdrm-tests.sh" "$work/tests/"
hash "$archive" > "$work/archive.sha256"
hash "$work/tests/libdrm.so.2.134.0" > "$work/library.sha256"
echo "PASS: cross-built libdrm, exact staged PLIST; run tests on EmberBSD: $work/tests"
echo 'Not package registration, a hardware test, or Mesa/session acceptance.'

#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted temporary headless Mesa cross diagnostic.
set -eu
[ "$#" -eq 8 ] || {
    echo 'Usage: build-mesa-diagnostic.sh ARCHIVE CROSS_PREFIX SYSROOT LIBDRM_PREFIX ZSTD_PREFIX MESON_DIR HOST_BISON NEW_WORK' >&2
    exit 2
}
archive=$1 prefix=$2 sysroot=$3 drm=$4 zstd=$5 meson=$6 bison=$7 work=$8
for path in "$@"; do
    case "$path" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths' >&2; exit 2;; esac
done
[ ! -e "$work" ] && [ ! -L "$work" ] || { echo 'Work already exists' >&2; exit 2; }
profile=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
recipe=$profile/../../pkgsrc/graphics/MesaLib
python=$(command -v "${PYTHON:-python3.15}")
pkg_config=$(command -v "${PKG_CONFIG:-pkg-config}")
ninja=$(command -v "${NINJA:-ninja}")
case "$ninja" in /*) ;; *) echo 'NINJA must resolve to an absolute path' >&2; exit 2;; esac
export NINJA=$ninja
cc=$prefix/bin/aarch64--netbsd-gcc
unset GCC_EXEC_PREFIX COMPILER_PATH LIBRARY_PATH CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH
[ "$("$cc" -dumpmachine)" = aarch64--netbsd ]
[ "$("$cc" -dumpfullversion)" = 16.2.0 ]
[ "$("$python" --version)" = 'Python 3.14.8' ]
[ "$("$python" "$meson/meson.py" --version)" = 1.12.1 ]
[ "$("$bison" --version | head -1)" = 'bison (GNU Bison) 3.8.2' ]
"$python" -c 'import mako, packaging, yaml'
for file in usr/include/stdlib.h usr/lib/crt0.o usr/lib/libm.so \
    usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0/crtbegin.o \
    usr/pkg/gcc16/include/c++/vector; do
    [ -f "$sysroot/$file" ] || { echo "Missing sysroot input: $file" >&2; exit 1; }
done
[ -f "$drm/lib/pkgconfig/libdrm.pc" ] && [ -f "$drm/lib/libdrm.so.2.134.0" ]
[ -f "$zstd/include/zstd.h" ] && [ -f "$zstd/lib/libzstd.so" ]
hash() { shasum -a 256 "$1" | awk '{print $1}'; }
expected=$(awk -F '\t' '$1=="graphics/MesaLib" {print $3}' "$profile/sources.tsv")
[ "$(hash "$archive")" = "$expected" ] || { echo 'Archive checksum mismatch' >&2; exit 1; }
mkdir "$work"
mkdir "$work/src" "$work/pkgconfig" "$work/host-bin"
for input in "$archive" "$cc" "$prefix/bin/aarch64--netbsd-g++" \
    "$prefix/libexec/gcc/aarch64--netbsd/16.2.0/cc1" \
    "$prefix/libexec/gcc/aarch64--netbsd/16.2.0/cc1plus" \
    "$python" "$meson/meson.py" "$bison" "$pkg_config" \
    "$ninja" "$(command -v flex)" "$(command -v ruby)" \
    "$drm/include/xf86drm.h" "$drm/include/xf86drmMode.h" \
    "$drm/lib/pkgconfig/libdrm.pc" "$zstd/include/zstd.h" \
    "$drm/lib/libdrm.so.2.134.0" "$zstd/lib/libzstd.so" \
    "$sysroot/usr/pkg/gcc16/lib/libstdc++.so.7.36" \
    "$sysroot/usr/pkg/gcc16/lib/libgcc_s.so.1" "$sysroot/usr/lib/libc.so" \
    "$sysroot/usr/lib/libm.so" "$sysroot/usr/lib/libpci.so" \
    "$sysroot/usr/include/stdlib.h" "$sysroot/usr/lib/crt0.o" \
    "$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0/crtbegin.o" \
    "$recipe/distinfo" "$recipe/patches/"patch-*; do
    shasum -a 256 "$input"
done > "$work/inputs.sha256"
{
    uname -a
    "$cc" --version
    "$python" --version
    "$python" "$meson/meson.py" --version
    "$bison" --version
    "$pkg_config" --version
    "$ninja" --version
    flex --version
    ruby --version
    "$python" -c 'import mako, packaging, yaml; print("Mako", mako.__version__, mako.__file__); print("packaging", packaging.__version__, packaging.__file__); print("PyYAML", yaml.__version__, yaml.__file__)'
} > "$work/tool-versions.txt"
tar -xJf "$archive" -C "$work/src" --strip-components=1
awk '/^SHA1 / {gsub(/[()]/,"",$2); print $2, $4}' "$recipe/distinfo" |
while read -r name expected_patch; do
    actual=$(sed '/[$]NetBSD.*/d' "$recipe/patches/$name" | shasum -a 1 | awk '{print $1}')
    [ "$actual" = "$expected_patch" ] || { echo "Patch checksum mismatch: $name" >&2; exit 1; }
    patch -f -N -F0 -p0 -d "$work/src" < "$recipe/patches/$name"
done > "$work/patch.log" 2>&1
if grep -Ei 'offset|fuzz' "$work/patch.log"; then
    echo 'Patch context drift is not accepted' >&2; exit 1
fi
sed "s,@PYTHONBIN@,$python,g" "$work/src/meson.build" > "$work/python-selection"
mv "$work/python-selection" "$work/src/meson.build"
sed "s,^prefix=/usr/pkg$,prefix=$drm," "$drm/lib/pkgconfig/libdrm.pc" > "$work/pkgconfig/libdrm.pc"
zstd_version=$(awk '$2=="ZSTD_VERSION_MAJOR" {a=$3} $2=="ZSTD_VERSION_MINOR" {b=$3} $2=="ZSTD_VERSION_RELEASE" {c=$3} END {print a "." b "." c}' "$zstd/include/zstd.h")
cat > "$work/pkgconfig/libzstd.pc" <<PC
prefix=$zstd
libdir=\${prefix}/lib
includedir=\${prefix}/include
Name: zstd
Description: Existing target zstd link inputs for temporary Mesa diagnostic
Version: $zstd_version
Libs: -L\${libdir} -lzstd
Cflags: -I\${includedir}
PC
cat > "$work/pkg-config" <<PC
#!/bin/sh
unset PKG_CONFIG_PATH PKG_CONFIG_SYSROOT_DIR
export PKG_CONFIG_LIBDIR='$work/pkgconfig'
exec '$pkg_config' "\$@"
PC
cat > "$work/host-bin/bison" <<BISON
#!/bin/sh
exec '$bison' "\$@"
BISON
chmod +x "$work/pkg-config" "$work/host-bin/bison"
PATH=$work/host-bin:$PATH
export PATH
[ "$("$work/pkg-config" --modversion libdrm)" = 2.4.134 ]
cat > "$work/cross.ini" <<CROSS
[binaries]
c = '$cc'
cpp = '$prefix/bin/aarch64--netbsd-g++'
ar = '$prefix/bin/aarch64--netbsd-ar'
strip = '$prefix/bin/aarch64--netbsd-strip'
nm = '$prefix/bin/aarch64--netbsd-nm'
pkg-config = '$work/pkg-config'
cmake = '/usr/bin/false'
[host_machine]
system = 'netbsd'
cpu_family = 'aarch64'
cpu = 'aarch64'
endian = 'little'
[properties]
needs_exe_wrapper = true
sys_root = '$sysroot'
[built-in options]
c_args = ['--sysroot=$sysroot', '-B$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0/']
cpp_args = ['--sysroot=$sysroot', '-B$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0/', '-isystem', '$sysroot/usr/pkg/gcc16/include/c++', '-isystem', '$sysroot/usr/pkg/gcc16/include/c++/aarch64--netbsd']
c_link_args = ['--sysroot=$sysroot', '-B$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0/', '-L$sysroot/usr/pkg/gcc16/lib', '-Wl,-rpath,/usr/pkg/gcc16/lib']
cpp_link_args = ['--sysroot=$sysroot', '-B$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0/', '-L$sysroot/usr/pkg/gcc16/lib', '-Wl,-rpath,/usr/pkg/gcc16/lib']
CROSS
cat > "$work/native.ini" <<NATIVE
[binaries]
python = '$python'
nm = '$prefix/bin/aarch64--netbsd-nm'
cmake = '/usr/bin/false'
NATIVE
"$python" "$meson/meson.py" setup "$work/build" "$work/src" \
    --cross-file="$work/cross.ini" --native-file="$work/native.ini" \
    --prefix=/usr/pkg --libdir=lib --buildtype=release --wrap-mode=nofallback \
    -Dgallium-drivers=virgl,softpipe -Dplatforms= -Dglx=disabled \
    -Degl=enabled -Dgbm=enabled -Dglvnd=disabled -Dgles1=enabled -Dgles2=enabled -Dopengl=true \
    -Dllvm=disabled -Dvulkan-drivers= -Dvulkan-layers= -Dtools= \
    -Dgallium-va=disabled -Dgallium-mediafoundation=disabled -Dgallium-rusticl=false \
    -Dteflon=false -Dperfetto=false -Dspirv-tools=disabled -Dmicrosoft-clc=disabled -Dallow-fallback-for= \
    -Dzlib=disabled -Dzstd=enabled -Dexpat=disabled -Dxmlconfig=disabled -Ddisplay-info=disabled \
    -Dlibunwind=disabled -Dvalgrind=disabled -Dbuild-tests=true -Db_lto=false \
    > "$work/configure.log" 2>&1
"$python" "$meson/meson.py" compile -C "$work/build" -j "${JOBS:-3}" > "$work/build.log" 2>&1
"$python" "$meson/meson.py" test -C "$work/build" --no-rebuild \
    'nir_algebraic_parser' 'egl-entrypoint-check' 'drirc xml validation' \
    'es1-ABI-check' 'es2-ABI-check' 'gbm-symbols-check' 'egl-symbols-check' \
    > "$work/host-tests.log" 2>&1
DESTDIR="$work/stage" "$python" "$meson/meson.py" install -C "$work/build" --no-rebuild > "$work/install.log" 2>&1
mkdir "$work/bundle"
cp -R "$work/stage/usr/pkg/lib" "$work/bundle/lib"
cp -P "$drm/lib/"libdrm.so* "$work/bundle/lib/"
cp -P "$sysroot/usr/pkg/gcc16/lib/libstdc++.so.7" "$sysroot/usr/pkg/gcc16/lib/libstdc++.so.7.36" \
    "$sysroot/usr/pkg/gcc16/lib/libgcc_s.so.1" "$work/bundle/lib/"
cp -P "$zstd/lib/"libzstd.so* "$sysroot/usr/lib/"libpci.so* "$work/bundle/lib/"
"$cc" --sysroot="$sysroot" -B"$sysroot/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0/" \
    -std=c11 -D_NETBSD_SOURCE -O2 -Wall -Wextra -Werror -I"$work/stage/usr/pkg/include" \
    "$profile/cross/mesa-render.c" -o "$work/bundle/mesa-render" \
    -L"$work/stage/usr/pkg/lib" -L"$sysroot/usr/pkg/gcc16/lib" -Wl,-rpath,/usr/pkg/gcc16/lib \
    -Wl,-rpath-link,"$work/stage/usr/pkg/lib" -Wl,-rpath-link,"$drm/lib" \
    -Wl,-rpath-link,"$zstd/lib" -Wl,-rpath-link,"$sysroot/usr/pkg/gcc16/lib" \
    -lEGL -lGLESv2 -lgbm -lm -pthread
cp "$profile/cross/run-mesa-diagnostic.sh" "$profile/cross/mesa-render.c" "$work/bundle/"
sh "$profile/cross/stage-mesa-tests.sh" "$work/build" "$work/src" "$work/bundle"
for file in "$work/bundle/lib/"*.so*; do
    "$prefix/bin/aarch64--netbsd-readelf" -d "$file"
done > "$work/libraries-elf.txt"
if grep -E 'RPATH|RUNPATH|NEEDED' "$work/libraries-elf.txt" | grep -F -e "$work" -e "$prefix" -e "$sysroot" -e "$drm" -e "$zstd"; then
    echo 'Build path leaked into staged ELF closure' >&2; exit 1
fi
hash "$archive" > "$work/archive.sha256"
(cd "$work/bundle"; find . -type f ! -name artifacts.sha256 -exec shasum -a 256 {} \; | LC_ALL=C sort -k2 > artifacts.sha256)
COPYFILE_DISABLE=1 tar --no-xattrs -czf "$work/mesa-diagnostic.tar.gz" -C "$work" bundle
hash "$work/mesa-diagnostic.tar.gz" > "$work/bundle.sha256"
echo "PASS: temporary headless Mesa build and host ABI checks; target render bundle: $work/mesa-diagnostic.tar.gz"
echo 'No LLVM/llvmpipe, X11/Wayland, XML configuration, zlib or installed-package acceptance.'

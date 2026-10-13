#!/bin/sh
# SPDX-License-Identifier: MIT
# Configure native macOS ARM64 Mesa tools. Do not alter a target Mesa tree.
set -eu
if [ "$#" -ne 5 ]; then
    echo "usage: $0 WORK MESA_SOURCE LLVM_SDK HOST_PREFIX DEP_PREFIX" >&2
    exit 2
fi
work=$1
mesa=$2
llvm=$3
host=$4
deps=$5
case "$work:$mesa:$llvm:$host:$deps" in
    *[[:space:]]*|*"'"*) echo 'Use absolute paths without shell whitespace or quotes.' >&2; exit 2 ;;
esac
for dir in "$work" "$mesa" "$llvm" "$host" "$deps"; do
    case "$dir" in /*) ;; *) echo "Not an absolute path: $dir" >&2; exit 2 ;; esac
done
[ "$(uname -s)" = Darwin ] && [ "$(uname -m)" = arm64 ]
[ "$("$llvm/bin/llvm-config" --version)" = 23.1.3 ]
[ "$(cat "$mesa/VERSION")" = 26.2.4 ]
macsdk=$(xcrun --sdk macosx --show-sdk-path)
mkdir -p "$work/tmp" "$work/cache/lto" "$work/logs"
export TMPDIR="$work/tmp"
export PATH="$work/venv/bin:$llvm/bin:$host/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export PKG_CONFIG_PATH="$deps/lib/pkgconfig:$host/lib/pkgconfig:/opt/homebrew/lib/pkgconfig"
# Use the current macOS C++ runtime explicitly. LLVM's -L path also contains
# a private libc++; it must not silently change the host runtime selection.
clink="-isysroot $macsdk -fuse-ld=lld -Wl,--lto-O1,--lto-CGO1"
cpplink="$clink -nostdlib++ $macsdk/usr/lib/libc++.tbd -Wl,-cache_path_lto,$work/cache/lto"
cat > "$work/native.ini" <<EOF
[binaries]
c = '$llvm/bin/clang'
cpp = '$llvm/bin/clang++'
objc = '$llvm/bin/clang'
ar = '$llvm/bin/llvm-ar'
llvm-config = '$llvm/bin/llvm-config'
pkg-config = '$host/bin/pkg-config'
[properties]
pkg_config_libdir = ['$deps/lib/pkgconfig', '$host/lib/pkgconfig', '/opt/homebrew/lib/pkgconfig', '/opt/homebrew/share/pkgconfig']
[built-in options]
c_args = ['-isysroot', '$macsdk']
cpp_args = ['-isysroot', '$macsdk']
objc_args = ['-isysroot', '$macsdk']
EOF
if [ -f "$work/mesa/meson-private/coredata.dat" ]; then
    set -- --reconfigure
else
    set --
fi
# Set link options explicitly. Reconfigure preserves options already cached
# in coredata even if the native file has changed.
"$host/bin/meson" setup "$@" "$work/mesa" "$mesa" \
    --native-file "$work/native.ini" --prefix "$work/prefix" \
    -Dc_link_args="$clink" -Dcpp_link_args="$cpplink" \
    -Dobjc_link_args="$clink" --buildtype debugoptimized \
    -Db_ndebug=false -Dcpp_rtti=false -Dauto_features=disabled \
    -Dplatforms=[] -Dgallium-drivers=[] -Dvulkan-drivers=[] \
    -Dglx=disabled -Degl=disabled -Dgbm=disabled -Dopengl=false \
    -Dgles1=disabled -Dgles2=disabled -Dtools=imagination \
    -Dmesa-clc=enabled -Dinstall-mesa-clc=true \
    -Dprecomp-compiler=enabled -Dinstall-precomp-compiler=true \
    -Dllvm=enabled -Dshared-llvm=disabled -Ddraw-use-llvm=false \
    -Damd-use-llvm=false -Dspirv-tools=enabled -Dbuild-tests=true
"$host/bin/ninja" -C "$work/mesa" -j "${JOBS:-4}"
"$host/bin/meson" install -C "$work/mesa" --no-rebuild

#!/bin/sh
# SPDX-License-Identifier: MIT
set -eu
if [ "$#" -ne 3 ]; then
    echo "usage: $0 WORK LLVM_SDK HOST_PREFIX" >&2
    exit 2
fi
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
root=$1
sdk=$2
host=$3
for dir in "$root" "$sdk" "$host"; do
    case "$dir" in /*) ;; *) echo "Not an absolute path: $dir" >&2; exit 2 ;; esac
done
[ "$("$sdk/bin/llvm-config" --version)" = 23.1.3 ]
check_source()
{
    name=$1
    rev=$2
    [ "$(git -C "$root/src/$name" rev-parse HEAD)" = "$rev" ]
    [ -z "$(git -C "$root/src/$name" status --porcelain)" ]
}
check_source SPIRV-Headers 496543121ce6419f23d6fa5d7194ba66c36212d2
ruby "$here/apply-spirv-tools-patches.rb" "$root/src/SPIRV-Tools"
check_source SPIRV-LLVM-Translator e65dde28ce8f12ef7245914fa2850260328669e4
mkdir -p "$root/tmp" "$root/cache/lto"
export TMPDIR="$root/tmp"
macsdk=$(xcrun --sdk macosx --show-sdk-path)
export PATH="$sdk/bin:$host/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export PKG_CONFIG_PATH="$root/prefix/lib/pkgconfig"
cmake -S "$root/src/SPIRV-Headers" -B "$root/build/headers" -G Ninja \
    -DCMAKE_INSTALL_PREFIX="$root/prefix" \
    -DSPIRV_HEADERS_ENABLE_TESTS=OFF
cmake --install "$root/build/headers"
cmake -S "$root/src/SPIRV-Tools" -B "$root/build/spirv-tools" -G Ninja \
    -DCMAKE_INSTALL_PREFIX="$root/prefix" \
    -DCMAKE_C_COMPILER="$sdk/bin/clang" \
    -DCMAKE_CXX_COMPILER="$sdk/bin/clang++" \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS_RELEASE=-O2 \
    -DCMAKE_OSX_SYSROOT="$macsdk" -DCMAKE_LINKER_TYPE=LLD \
    -DCMAKE_EXE_LINKER_FLAGS="-Wl,--lto-O1,--lto-CGO1 -nostdlib++ $macsdk/usr/lib/libc++.tbd -Wl,-cache_path_lto,$root/cache/lto" \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -DSPIRV-Headers_SOURCE_DIR="$root/src/SPIRV-Headers" \
    -DPython3_EXECUTABLE="$host/bin/python3.14" \
    -DSPIRV_SKIP_TESTS=ON -DSPIRV_SKIP_EXECUTABLES=OFF \
    -DBUILD_SHARED_LIBS=OFF -DSPIRV_WERROR=ON
cmake --build "$root/build/spirv-tools" --parallel "${JOBS:-4}"
# A new directory preserves earlier causal and acceptance receipts.
order_test=$(mktemp -d "$root/build/link-order.XXXXXXXX")
ruby "$here/check-spirv-link-order.rb" "$root/build/spirv-tools/tools" "$order_test/result"
cmake --install "$root/build/spirv-tools"
cmake -S "$root/src/SPIRV-LLVM-Translator" -B "$root/build/translator" -G Ninja \
    -DCMAKE_INSTALL_PREFIX="$root/prefix" \
    -DCMAKE_C_COMPILER="$sdk/bin/clang" \
    -DCMAKE_CXX_COMPILER="$sdk/bin/clang++" \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS_RELEASE=-O2 \
    -DCMAKE_OSX_SYSROOT="$macsdk" -DCMAKE_LINKER_TYPE=LLD \
    -DCMAKE_EXE_LINKER_FLAGS="-Wl,--lto-O1,--lto-CGO1 -nostdlib++ $macsdk/usr/lib/libc++.tbd -Wl,-cache_path_lto,$root/cache/lto" \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -DLLVM_DIR="$sdk/lib/cmake/llvm" \
    -DLLVM_EXTERNAL_SPIRV_HEADERS_SOURCE_DIR="$root/src/SPIRV-Headers" \
    -DLLVM_SPIRV_INCLUDE_TESTS=OFF -DLLVM_ENABLE_ASSERTIONS=ON \
    -DLLVM_SPIRV_ENABLE_LIBSPIRV_DIS=ON -DBUILD_SHARED_LIBS=OFF
cmake --build "$root/build/translator" --parallel "${JOBS:-4}"
cmake --install "$root/build/translator"

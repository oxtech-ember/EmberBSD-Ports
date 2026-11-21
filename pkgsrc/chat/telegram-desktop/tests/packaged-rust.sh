#!/bin/sh
# Run with the SDK tools in PATH and the patched Telegram source tree.
set -eu
src=$(cd "${1:?usage: packaged-rust.sh PATCHED_TELEGRAM_SOURCE}" && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/provider/lib/pkgconfig"
cat > "$tmp/CMakeLists.txt" <<'EOF'
cmake_minimum_required(VERSION 3.25)
project(packaged_rust NONE)
set(DESKTOP_APP_USE_PACKAGED ON)
add_subdirectory("${TELEGRAM_SOURCE}/cmake/external/tdesktop_rust" provider)
if (EXPECT_PROVIDER)
    get_target_property(deps external_tdesktop_rust INTERFACE_LINK_LIBRARIES)
    if (NOT "-lm" IN_LIST deps)
        message(FATAL_ERROR "Missing static dependency from the provider")
    endif()
endif()
EOF
configure() {
    PKG_CONFIG_PATH= PKG_CONFIG_LIBDIR="$tmp/provider/lib/pkgconfig" \
        cmake -G Ninja -S "$tmp" -B "$tmp/$1" -DTELEGRAM_SOURCE="$src" \
        -DCMAKE_FIND_ROOT_PATH="$tmp/provider" -DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=ONLY \
        -DCMAKE_LIBRARY_PATH=/lib -DEXPECT_PROVIDER="$2"
}
if configure absent OFF > "$tmp/log" 2>&1; then
    echo "Packaged build accepted a missing combined Rust provider" >&2
    exit 1
fi
grep -q 'DESKTOP_APP_TDESKTOP_RUST_LIBRARY' "$tmp/log" || { cat "$tmp/log" >&2; exit 1; }
llvm-ar cr "$tmp/provider/lib/libtdesktop_rust.a"
cat > "$tmp/provider/lib/pkgconfig/tdesktop-rust.pc" <<EOF
Name: tdesktop-rust
Description: Telegram Rust provider test fixture
Version: 1.0
Libs: -L$tmp/provider/lib -ltdesktop_rust
Libs.private: -lm
EOF
configure present ON
echo 'PASS: packaged Telegram requires its combined Rust archive and propagates its static dependencies'

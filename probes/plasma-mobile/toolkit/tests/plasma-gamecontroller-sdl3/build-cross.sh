#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
set -eu
if [ "$#" -ne 5 ]; then
    echo "usage: $0 GAMECONTROLLER_SOURCE BUILD_DIR SYSROOT TOOLCHAIN QT_HOST_PATH" >&2
    exit 2
fi
for path in "$@"; do
    case "$path" in /*) ;; *) echo "All paths must be absolute" >&2; exit 2 ;; esac
done
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ -n "${EMBER_TEST_CLANG:-}" ]; then
    case "$EMBER_TEST_CLANG" in /*) ;; *) echo "EMBER_TEST_CLANG must be absolute" >&2; exit 2 ;; esac
fi
cmake -S "$script_dir" -B "$2" -G Ninja \
    -DEMBER_TEST_CLANG="${EMBER_TEST_CLANG:-}" -DEMBER_TEST_UBSAN="${EMBER_TEST_UBSAN:-OFF}" \
    -DGAMECONTROLLER_SOURCE="$1" \
    -DCMAKE_TOOLCHAIN_FILE="$script_dir/cross.cmake" \
    -DEMBER_TEST_SYSROOT="$3" -DEMBER_TEST_TOOLCHAIN="$4" \
    -DQT_HOST_PATH="$5" -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    '-DEMBER_TEST_EXTRA_FLAGS=-Wall;-Wextra;-D_FORTIFY_SOURCE=2;-fstack-protector-strong'
cmake --build "$2" --parallel "${MAKE_JOBS:-2}"

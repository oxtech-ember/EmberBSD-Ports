#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
set -eu
[ "$#" -eq 3 ] || { echo "Usage: $0 DISTFILES NEW_WORK QT_PREFIX" >&2; exit 2; }
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
archive=$1/plasma-pa-6.8.0.tar.xz
expected=$(awk -F '\t' '$1 == "audio/plasma6-plasma-pa" {print $3}' "$root/sources.tsv")
[ -n "$expected" ] && [ "$(shasum -a 256 "$archive" | awk '{print $1}')" = "$expected" ] || {
    echo 'Plasma PA source checksum differs' >&2; exit 1;
}
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
tar -xJf "$archive" -C "$work" plasma-pa-6.8.0/src/percentvalidator.cpp \
    plasma-pa-6.8.0/src/percentvalidator.h plasma-pa-6.8.0/autotests/percentvalidatortest.cpp
cat > "$work/CMakeLists.txt" <<'CMAKE'
cmake_minimum_required(VERSION 3.21)
project(PlasmaPercentSourceTest LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
find_package(Qt6 6.12 REQUIRED COMPONENTS Core Gui Qml Test)
add_executable(percentvalidatortest plasma-pa-6.8.0/src/percentvalidator.cpp
    plasma-pa-6.8.0/src/percentvalidator.h plasma-pa-6.8.0/autotests/percentvalidatortest.cpp)
target_include_directories(percentvalidatortest PRIVATE plasma-pa-6.8.0/src)
target_link_libraries(percentvalidatortest PRIVATE Qt6::Core Qt6::Gui Qt6::Qml Qt6::Test)
target_compile_options(percentvalidatortest PRIVATE -fsanitize=address,undefined -fno-omit-frame-pointer)
target_link_options(percentvalidatortest PRIVATE -fsanitize=address,undefined)
CMAKE
"${CMAKE:-cmake}" -S "$work" -B "$work/build" -DCMAKE_PREFIX_PATH="$3" \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
"${CMAKE:-cmake}" --build "$work/build" --parallel 2
ASAN_OPTIONS=halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 \
    "$work/build/percentvalidatortest"
echo 'PASS: upstream percent validator on the host with ASan/UBSan; target runtime is separate'

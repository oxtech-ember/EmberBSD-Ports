#!/bin/sh
set -eu

: "${CXX:?Set CXX to the selected native Clang++}"
test_dir=$(CDPATH= cd "$(dirname "$0")" && pwd)
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/ksystemstats-ifaddrs.XXXXXXXX")
trap 'rm -rf "$work_dir"' EXIT HUP INT TERM

"$CXX" -std=c++17 -g -O1 -fsanitize=address -fno-omit-frame-pointer \
    -I "$test_dir/ifaddrs-stubs" \
    "$test_dir/network-ifaddrs-lifetime.cpp" \
    -o "$work_dir/network-ifaddrs-lifetime"

ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 \
    "$work_dir/network-ifaddrs-lifetime"

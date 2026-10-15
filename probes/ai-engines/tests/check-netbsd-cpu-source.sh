#!/bin/sh
# SPDX-License-Identifier: MIT
set -eu
[ "$#" = 1 ] || { echo 'Usage: check-netbsd-cpu-source.sh WORK' >&2; exit 2; }
work=$1
tests=$(CDPATH= cd "$(dirname "$0")" && pwd)
"${CXX:-c++}" -std=c++20 -Wall -Wextra -Werror -pthread \
    -I "$work/src/onnxruntime-1.31.0/onnxruntime" \
    "$tests/netbsd-cpu-source.cpp" -o "$work/netbsd-cpu-source-contract"
"$work/netbsd-cpu-source-contract"

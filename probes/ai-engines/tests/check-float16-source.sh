#!/bin/sh
# SPDX-License-Identifier: MIT
set -eu
[ "$#" = 1 ] || { echo 'Usage: check-float16-source.sh WORK' >&2; exit 2; }
work=$1
source=$work/src/onnxruntime-1.31.0
deps=$work/onnx-build/_deps
tests=$(CDPATH= cd "$(dirname "$0")" && pwd)
"${CXX:-c++}" -std=c++20 -Wall -Wextra -Werror \
    -I "$source/include/onnxruntime" -I "$deps/gsl-src/include" \
    -I "$deps/abseil_cpp-src" "$tests/float16-source.cpp" \
    -o "$work/float16-source-contract"
"$work/float16-source-contract"

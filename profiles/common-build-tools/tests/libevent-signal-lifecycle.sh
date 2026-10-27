#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
set -eu
test_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source=$1
work=$2
cmake=$3
gmake=$4
mkdir -p "$work"
"$cmake" -S "$source" -B "$work/build" -G 'Unix Makefiles' \
  -DCMAKE_MAKE_PROGRAM="$gmake" -DCMAKE_C_COMPILER="$CC" \
  -DCMAKE_AR="$AR" -DCMAKE_RANLIB="$RANLIB" -DCMAKE_OSX_SYSROOT="$5" \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DEVENT__LIBRARY_TYPE=STATIC -DEVENT__DISABLE_OPENSSL=ON \
  -DEVENT__DISABLE_TESTS=ON -DEVENT__DISABLE_SAMPLES=ON \
  -DEVENT__DISABLE_BENCHMARK=ON
"$cmake" --build "$work/build" --target event_core_static --parallel 2
"$CC" -std=c11 -Wall -Werror -I"$source/include" -I"$work/build/include" \
  "$test_dir/libevent-signal-lifecycle.c" "$work/build/lib/libevent_core.a" -o "$work/check"
"$work/check"

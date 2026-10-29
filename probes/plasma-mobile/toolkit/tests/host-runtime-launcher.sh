#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Verify native custom commands see a selected runtime after Ninja's shell.
set -eu
[ "$#" = 5 ] || { echo 'Usage: host-runtime-launcher.sh CC CMAKE NINJA PYTHON SDK_SOURCE' >&2; exit 2; }
cc=$1 cmake=$2 ninja=$3 python=$4 sdk=$5
case "$(uname -s)" in Darwin) ;; *) echo 'Darwin required' >&2; exit 2;; esac
root=$(CDPATH= cd -- "$(dirname -- "$0")/../cross" && pwd)
tmp=$(mktemp -d "${TMPDIR:-/tmp}/ember-qt-launcher.XXXXXXXX")
trap 'rm -rf "$tmp"' EXIT HUP INT TERM
mkdir "$tmp/view" "$tmp/src"
cat > "$tmp/src/lib.c" <<'SRC'
int stage_value(void) { return 42; }
SRC
cat > "$tmp/src/tool.c" <<'SRC'
#include <stdio.h>
int stage_value(void);
int main(void) { printf("%d\n", stage_value()); return 0; }
SRC
"$cc" -dynamiclib "$tmp/src/lib.c" -Wl,-install_name,"$tmp/logical/libstage.dylib" -o "$tmp/view/libstage.dylib"
"$cc" "$tmp/src/tool.c" -L"$tmp/view" -lstage -o "$tmp/tool"
if "$tmp/tool" >"$tmp/no-view.log" 2>&1; then echo 'Unbound tool unexpectedly loaded stage DSO' >&2; exit 1; fi
cat > "$tmp/src/CMakeLists.txt" <<'CMAKE'
cmake_minimum_required(VERSION 3.29)
project(runtime_test NONE)
add_custom_command(OUTPUT result COMMAND "${TEST_TOOL}" > result)
add_custom_target(run ALL DEPENDS result)
CMAKE
QT_NATIVE_RUNTIME_PYTHON=$python QT_NATIVE_RUNTIME_LAUNCHER=$sdk/scripts/run-darwin-with-runtime.py QT_NATIVE_RUNTIME_VIEW=$tmp/view
export QT_NATIVE_RUNTIME_PYTHON QT_NATIVE_RUNTIME_LAUNCHER QT_NATIVE_RUNTIME_VIEW
"$cmake" -S "$tmp/src" -B "$tmp/build" -G Ninja -DCMAKE_MAKE_PROGRAM="$ninja" -DTEST_TOOL="$tmp/tool" -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES="$root/native-host-runtime.cmake" >"$tmp/configure.log" 2>&1
"$ninja" -C "$tmp/build" >"$tmp/build.log" 2>&1
grep -F -x 42 "$tmp/build/result" >/dev/null
echo 'Qt native runtime launcher PASS'

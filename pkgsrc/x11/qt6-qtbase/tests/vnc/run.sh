#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted). Real installed VNC lifecycle.
set -eu
[ "$#" = 2 ] || { echo 'Usage: run.sh NATIVE_QT_PREFIX NEW_OUT' >&2; exit 2; }
qt=$1 out=$2
for path do case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2;; esac; done
[ -d "$qt/include/QtGui" ] && [ -d "$qt/plugins/platforms" ] || exit 2
[ ! -e "$out" ] && [ ! -L "$out" ] || { echo 'Output path already exists.' >&2; exit 2; }
source=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
mkdir "$out"
cxx=${CXX:-c++}
"$cxx" --version > "$out/compiler-version.txt"
"$cxx" -dumpfullversion -dumpversion > "$out/compiler-fullversion.txt"
case "$(cat "$out/compiler-fullversion.txt")" in 16.*) ;; *) echo 'Use the native GCC16 compiler.' >&2; exit 2;; esac
valgrind --version > "$out/valgrind-version.txt"
cmake -S "$source" -B "$out/build" -DCMAKE_CXX_COMPILER="$cxx" \
    -DCMAKE_PREFIX_PATH="$qt" -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON > "$out/configure.log" 2>&1
cmake --build "$out/build" -j2 > "$out/build.log" 2>&1
printf '%s\n' 'QT_QPA_PLATFORM=vnc:size=160x128:port=0' \
    "QT_PLUGIN_PATH=$qt/plugins" "LD_LIBRARY_PATH=$qt/lib:${LD_LIBRARY_PATH:-}" \
    'No VNC client or displayed-frame acceptance is claimed by this lifecycle test.' > "$out/runtime-environment.txt"
status=0
env QT_QPA_PLATFORM=vnc:size=160x128:port=0 QT_PLUGIN_PATH="$qt/plugins" \
    LD_LIBRARY_PATH="$qt/lib:${LD_LIBRARY_PATH:-}" \
    valgrind --tool=memcheck --leak-check=full --show-leak-kinds=all \
        --errors-for-leak-kinds=definite,indirect,possible --error-exitcode=99 \
        --default-suppressions=no --log-file="$out/memcheck.log" \
        "$out/build/qt-vnc-lifecycle" > "$out/runtime.stdout" 2> "$out/runtime.stderr" || status=$?
printf '%s\n' "$status" > "$out/runtime.status"
exit "$status"

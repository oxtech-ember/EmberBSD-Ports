#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# Check an actual bootstrap CMake without installing a sibling shell.
set -eu
if [ "$#" -ne 3 ]; then
    echo "usage: $0 /absolute/Bootstrap.cmk/cmake /absolute/gmake /absolute/mksh" >&2
    exit 2
fi
cmake=$1
make=$2
shell=$3
for tool in "$cmake" "$make" "$shell"; do
    case "$tool" in /*) ;; *) echo "tool path must be absolute: $tool" >&2; exit 2;; esac
    test -x "$tool"
done
test ! -e "${cmake%/*}/${shell##*/}"
work=$(mktemp -d "${TMPDIR:-/tmp}/cmake-bootstrap-shell.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
mkdir "$work/source"
cat > "$work/source/CMakeLists.txt" <<'EOF'
cmake_minimum_required(VERSION 3.20)
project(bootstrap_shell NONE)
add_custom_target(probe ALL
  COMMAND "${CMAKE_COMMAND}" -E echo "bootstrap shell executed"
  VERBATIM)
EOF
"$cmake" -S "$work/source" -B "$work/build" -G 'Unix Makefiles' \
    "-DCMAKE_MAKE_PROGRAM=$make"
expected=$(printf '%s' "$shell" | sed 's/ /\\ /g')
grep -Fx "SHELL = $expected" "$work/build/Makefile"
"$make" -C "$work/build" probe > "$work/build.log" 2>&1 || {
    cat "$work/build.log" >&2
    exit 1
}
grep -F 'bootstrap shell executed' "$work/build.log"
echo 'PASS: bootstrap uses the selected shell without a sibling provider'

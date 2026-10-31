#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake cross-cmake-python-backend.sh PKGSRC MAKECONF
#
# Python build backends such as scikit-build-core start CMake themselves and
# take extra arguments only from CMAKE_ARGS. Without the cross settings,
# CMake configured py-pybind11 for the build host and passed the Darwin
# -search_paths_first to ld.lld. Configure a C project with the arguments
# scikit-build-core derives from the build environment of a cross recipe
# (archivers/lz4: C only, no dependencies) and its wrapped compiler.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
recipe=$1/archivers/lz4 makeconf=$2
bm() { MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$recipe" MAKECONF="$makeconf" "$@"; }
[ "$(bm -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] && [ "$(bm -V '${OPSYS}')" = NetBSD ] ||
	{ echo "$0: select a MAKECONF for a NetBSD cross build" >&2; exit 2; }
python=$(bm -V '${TOOLBASE}/bin/python3.15')
cmake=$(bm -V '${TOOLBASE}/bin/cmake')
ninja=$(bm -V '${TOOLBASE}/bin/ninja')
make_env=$(bm -V '${MAKE_ENV}')
tmp=$(mktemp -d "${TMPDIR:-/tmp}/cmake-backend.XXXXXX")
trap 'rm -rf "$tmp"; bm clean >/dev/null 2>&1 || :' EXIT
bm clean >/dev/null 2>&1 || :
bm wrapper >/dev/null 2>&1 || { echo "FAIL: wrapper"; exit 1; }
printf 'cmake_minimum_required(VERSION 3.15)\nproject(backend C)\nadd_executable(probe probe.c)\n' >"$tmp/CMakeLists.txt"
printf 'int main(void) { return 0; }\n' >"$tmp/probe.c"
cat >"$tmp/configure.py" <<'PY'
import os, subprocess, sys, types
from scikit_build_core.builder.builder import get_cmake_args_from_settings
settings = types.SimpleNamespace(cmake=types.SimpleNamespace(args=[]))
args = get_cmake_args_from_settings(settings, os.environ)
cmake, ninja, src = sys.argv[1:4]
sys.exit(subprocess.call([cmake, '-S', src, '-B', src + '/build', '-G', 'Ninja',
                          '-DCMAKE_MAKE_PROGRAM=' + ninja, *args]))
PY
status=0
eval "env $make_env \"\$python\" \"\$tmp/configure.py\" \"\$cmake\" \"\$ninja\" \"\$tmp\"" \
	>"$tmp/configure.log" 2>&1 || { sed -n '/error:/p' "$tmp/configure.log" | head -5; status=1; }
system=$(sed -n 's/^set(CMAKE_SYSTEM_NAME "\(.*\)")$/\1/p' "$tmp"/build/CMakeFiles/*/CMakeSystem.cmake 2>/dev/null || :)
[ "$system" = NetBSD ] || { echo "FAIL: CMake system is '${system}'"; status=1; }
[ "$status" -eq 0 ] || exit 1
echo "PASS: CMake started by a Python build backend configures the NetBSD target"

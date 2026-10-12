#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), upstream host-only Polkit policy generator.
set -eu
[ "$#" = 6 ] || { echo 'Usage: build-kauth-tool.sh DISTFILES HOST_QT NATIVE_PREFIX ECM_CMAKE_DIR HOST_COREADDONS NEW_WORK' >&2; exit 2; }
dist=$1 qt=$2 native=$3 ecm=$4 core=$5 work=$6
: "${CMAKE:?}" "${NINJA:?}" "${HOST_CC:?}" "${HOST_CXX:?}"
: "${JOBS:=2}"
for path in "$dist" "$qt" "$native" "$ecm" "$core" "$work" "$CMAKE" "$NINJA" "$HOST_CC" "$HOST_CXX"; do
    case "$path" in /*) ;; *) exit 2;; esac
    case "$path" in *[!a-zA-Z0-9_./+-]*) exit 2;; esac
done
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
archive=kauth-6.31.0.tar.xz
expected=$(awk -F '\t' -v name="$archive" '$2 == name {print $3}' "$root/sources.tsv")
[ -n "$expected" ] && [ "$(shasum -a 256 "$dist/$archive" | awk '{print $1}')" = "$expected" ]
[ "$("$qt/bin/qmake" -query QT_VERSION)" = 6.12.0 ]
mkdir "$work"
mkdir "$work/source" "$work/tooling" "$work/tooling/KF6Auth"
tar -xf "$dist/$archive" --strip-components=1 -C "$work/source"
"$CMAKE" -S "$work/source" -B "$work/build" -G Ninja \
    -DCMAKE_MAKE_PROGRAM="$NINJA" -DCMAKE_C_COMPILER="$HOST_CC" -DCMAKE_CXX_COMPILER="$HOST_CXX" \
    -DCMAKE_PREFIX_PATH="$core;$qt;$native" -DECM_DIR="$ecm" -DCMAKE_BUILD_TYPE=Release \
    -DKAUTH_BUILD_CODEGENERATOR_ONLY=ON -DKAUTH_BACKEND_NAME=POLKITQT6-1 \
    -DCMAKE_INSTALL_PREFIX="$work/prefix" -DCMAKE_EXPORT_COMPILE_COMMANDS=ON > "$work/configure.log" 2>&1
"$CMAKE" --build "$work/build" --parallel "$JOBS" > "$work/build.log" 2>&1
"$CMAKE" --install "$work/build" > "$work/install.log" 2>&1
program=$work/build/bin/kauth-policy-gen
[ -x "$program" ]
"$program" "$work/source/autotests/foo_actions.actions" "$work/foo.policy"
cmp "$work/source/autotests/foo.policy" "$work/foo.policy"
if "$program" > "$work/missing-argument.log" 2>&1; then exit 1; fi
cat > "$work/tooling/KF6Auth/KF6AuthToolsTargets.cmake" <<CMAKE
if(NOT TARGET KF6::kauth-policy-gen)
  add_executable(KF6::kauth-policy-gen IMPORTED GLOBAL)
  set_target_properties(KF6::kauth-policy-gen PROPERTIES IMPORTED_LOCATION "$program")
endif()
CMAKE
shasum -a 256 "$dist/$archive" "$program" "$work/foo.policy" "$0" > "$work/outputs.sha256"
echo 'PASS: native Polkit policy generator, exact upstream fixture and missing-argument rejection'

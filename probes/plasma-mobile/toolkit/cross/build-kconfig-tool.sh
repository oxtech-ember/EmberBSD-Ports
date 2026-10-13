#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Build the upstream native KConfig generator.
set -eu
[ "$#" = 4 ] || { echo "Usage: $0 DISTFILES HOST_QT ECM_CMAKE_DIR NEW_WORK" >&2; exit 2; }
distfiles=$1 qt=$2 ecm=$3 work=$4
: "${CMAKE:?Set native CMake}"
: "${NINJA:?Set native Ninja}"
: "${HOST_CC:?Set native C compiler}"
: "${HOST_CXX:?Set native C++ compiler}"
: "${JOBS:=2}"
for path in "$distfiles" "$qt" "$ecm" "$work" "$CMAKE" "$NINJA" "$HOST_CC" "$HOST_CXX"; do
    case "$path" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2;; esac
    case "$path" in *[!a-zA-Z0-9_./+-]*) echo 'Use paths without shell/CMake metacharacters' >&2; exit 2;; esac
done
[ "$("$qt/bin/qmake" -query QT_VERSION)" = 6.12.0 ]
toolkit=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
archive=kconfig-6.31.0.tar.xz
expected=$(awk -F '\t' '$1 == "devel/kf6-kconfig" { print $3 }' "$toolkit/sources.tsv")
[ -n "$expected" ] && [ "$(shasum -a 256 "$distfiles/$archive" | awk '{print $1}')" = "$expected" ]
mkdir "$work"
mkdir "$work/source" "$work/tooling" "$work/tooling/KF6Config"
tar -xf "$distfiles/$archive" -C "$work/source"
"$CMAKE" --build "$qt" --target Xml --parallel "$JOBS" > "$work/qt-xml-build.log" 2>&1
# This private native build exists solely to produce kconfig_compiler. The full
# target package independently keeps its Gui, Qml, Quick and DBus components.
"$CMAKE" -S "$work/source/kconfig-6.31.0" -B "$work/build" -G Ninja \
    -DCMAKE_MAKE_PROGRAM="$NINJA" -DCMAKE_C_COMPILER="$HOST_CC" -DCMAKE_CXX_COMPILER="$HOST_CXX" \
    -DCMAKE_PREFIX_PATH="$qt" -DECM_DIR="$ecm" -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_TESTING=OFF -DKCONFIG_USE_GUI=OFF -DKCONFIG_USE_QML=OFF -DUSE_DBUS=OFF \
    -DQt6LinguistTools_DIR="$qt/lib/cmake/Qt6LinguistTools" > "$work/configure.log" 2>&1
"$CMAKE" --build "$work/build" --target kconfig_compiler kconf_update --parallel "$JOBS" > "$work/build.log" 2>&1
"$work/build/bin/kconfig_compiler_kf6" --version > "$work/version.txt"
grep -qx 'kconfig_compiler 6.31.0' "$work/version.txt"
file "$work/build/bin/kconf_update" | grep -q 'Mach-O'
cat > "$work/tooling/KF6Config/KF6ConfigCompilerTargets.cmake" <<EOF
# Native build tools only; do not expose host target libraries to consumers.
if(NOT TARGET KF6::kconfig_compiler)
add_executable(KF6::kconfig_compiler IMPORTED)
set_target_properties(KF6::kconfig_compiler PROPERTIES
  IMPORTED_LOCATION "$work/build/bin/kconfig_compiler_kf6")
endif()
if(NOT TARGET KF6::kconf_update)
add_executable(KF6::kconf_update IMPORTED)
set_target_properties(KF6::kconf_update PROPERTIES
  IMPORTED_LOCATION "$work/build/bin/kconf_update")
endif()
EOF
shasum -a 256 "$0" "$distfiles/$archive" "$work/build/bin/kconfig_compiler_kf6" "$work/build/bin/kconf_update" > "$work/inputs-output.sha256"
file "$work/build/bin/kconfig_compiler_kf6" "$work/build/bin/kconf_update" > "$work/architecture.txt"
printf 'Built KF6_HOST_TOOLING=%s\n' "$work/tooling"

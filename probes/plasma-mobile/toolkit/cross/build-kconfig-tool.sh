#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Build the upstream native KConfig generator.
set -eu
[ "$#" = 4 ] || { echo "Usage: $0 DISTFILES HOST_QT ECM_CMAKE_DIR NEW_WORK" >&2; exit 2; }
distfiles=$1 qt=$2 ecm=$3 work=$4
: "${CMAKE:?Set native CMake}"
: "${NINJA:?Set native Ninja}"
: "${TAR:?Set native tar}"
: "${HOST_READOBJ:?Set native llvm-readobj}"
: "${HOST_PYTHON:?Set native Python}"
: "${HOST_OBJECT_ARCH:?Set the native object architecture reported by llvm-readobj}"
HOST_RUNTIME_VIEW=${HOST_RUNTIME_VIEW:-}
if [ -n "$HOST_RUNTIME_VIEW" ]; then
    : "${HOST_SDK_SOURCE:?Set SDK source}"
fi
: "${HOST_CC:?Set native C compiler}"
: "${HOST_CXX:?Set native C++ compiler}"
: "${HOST_PACKAGE_PREFIX:?Set native dependency prefix}"
: "${JOBS:=2}"
for path in "$distfiles" "$qt" "$ecm" "$work" "$CMAKE" "$NINJA" "$TAR" "$HOST_READOBJ" "$HOST_PYTHON" "$HOST_CC" "$HOST_CXX" "$HOST_PACKAGE_PREFIX"; do
    case "$path" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2;; esac
    case "$path" in *[!a-zA-Z0-9_./+-]*) echo 'Use paths without shell/CMake metacharacters' >&2; exit 2;; esac
done
run_native() {
    if [ -n "$HOST_RUNTIME_VIEW" ]; then
        "$HOST_PYTHON" -I -S "$HOST_SDK_SOURCE/scripts/run-darwin-with-runtime.py" --runtime-view "$HOST_RUNTIME_VIEW" -- "$@"
    else
        "$@"
    fi
}
[ "$(run_native "$qt/bin/qmake" -query QT_VERSION)" = 6.12.0 ]
for module in Core Xml LinguistTools; do
    [ -f "$qt/lib/cmake/Qt6$module/Qt6${module}Config.cmake" ] || {
        echo "Missing native Qt module: $module" >&2; exit 2;
    }
done

toolkit=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
archive=kconfig-6.31.0.tar.xz
expected=$(awk -F '\t' '$1 == "devel/kf6-kconfig" { print $3 }' "$toolkit/sources.tsv")
[ -n "$expected" ] && [ "$(shasum -a 256 "$distfiles/$archive" | awk '{print $1}')" = "$expected" ]
mkdir "$work"
mkdir "$work/source" "$work/tooling" "$work/tooling/KF6Config"
"$TAR" -xf "$distfiles/$archive" -C "$work/source"
# The caller holds the Qt work shared; build missing Xml separately under the
# Qt producer's exclusive lock instead of mutating the reader's input.
{ [ -s "$qt/lib/QtXml.framework/Versions/A/QtXml" ] || [ -s "$qt/lib/libQt6Xml.so" ]; } || {
    echo 'Build the native Qt Xml target before this generator' >&2; exit 2;
}
# This private native build exists solely to produce kconfig_compiler. The full
# target package independently keeps its Gui, Qml, Quick and DBus components.
"$CMAKE" -S "$work/source/kconfig-6.31.0" -B "$work/build" -G Ninja \
    -DCMAKE_MAKE_PROGRAM="$NINJA" -DCMAKE_C_COMPILER="$HOST_CC" -DCMAKE_CXX_COMPILER="$HOST_CXX" \
    -DCMAKE_PREFIX_PATH="$qt;$HOST_PACKAGE_PREFIX" -DECM_DIR="$ecm" -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_FIND_USE_CMAKE_SYSTEM_PATH=OFF -DCMAKE_FIND_USE_CMAKE_ENVIRONMENT_PATH=OFF \
    -DCMAKE_FIND_USE_PACKAGE_REGISTRY=OFF -DCMAKE_FIND_USE_SYSTEM_PACKAGE_REGISTRY=OFF \
    -DQt6_DIR="$qt/lib/cmake/Qt6" -DQt6Core_DIR="$qt/lib/cmake/Qt6Core" \
    -DQt6Xml_DIR="$qt/lib/cmake/Qt6Xml" \
    -DBUILD_TESTING=OFF -DKCONFIG_USE_GUI=OFF -DKCONFIG_USE_QML=OFF -DUSE_DBUS=OFF \
    -DQt6LinguistTools_DIR="$qt/lib/cmake/Qt6LinguistTools" > "$work/configure.log" 2>&1
"$CMAKE" --build "$work/build" --target kconfig_compiler kconf_update --parallel "$JOBS" > "$work/build.log" 2>&1
run_native "$work/build/bin/kconfig_compiler_kf6" --version > "$work/version.txt"
grep -qx 'kconfig_compiler 6.31.0' "$work/version.txt"
"$HOST_READOBJ" --file-headers "$work/build/bin/kconf_update" > "$work/architecture.txt"
case "$(uname -s)" in Darwin) host_format="Format: Mach-O" ;; Linux) host_format="Format: ELF" ;; *) echo "Unsupported native object format" >&2; exit 2 ;; esac
grep -F "$host_format" "$work/architecture.txt" >/dev/null || { echo "Wrong native kconf_update object format" >&2; exit 1; }
grep -F -x "Arch: $HOST_OBJECT_ARCH" "$work/architecture.txt" >/dev/null || { echo "Wrong native kconf_update architecture" >&2; exit 1; }
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
"$HOST_READOBJ" --file-headers "$work/build/bin/kconfig_compiler_kf6" > "$work/compiler-architecture.txt"
grep -F "$host_format" "$work/compiler-architecture.txt" >/dev/null || { echo "Wrong native kconfig_compiler object format" >&2; exit 1; }
grep -F -x "Arch: $HOST_OBJECT_ARCH" "$work/compiler-architecture.txt" >/dev/null || { echo "Wrong native kconfig_compiler architecture" >&2; exit 1; }
printf 'Built KF6_HOST_TOOLING=%s\n' "$work/tooling"

#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), native KPackage metadata generator.
set -eu
[ "$#" = 6 ] || { echo 'Usage: build-kpackage-tool.sh DISTFILES HOST_QT NATIVE_PREFIX ECM_CMAKE_DIR HOST_DOCTOOLS NEW_WORK' >&2; exit 2; }
distfiles=$1 qt=$2 native=$3 ecm=$4 doctools=$5 work=$6
: "${CMAKE:?Set native CMake}" "${NINJA:?Set native Ninja}" "${HOST_CC:?Set native C compiler}" "${HOST_CXX:?Set native C++ compiler}"
: "${JOBS:=2}"
for item in "$distfiles" "$qt" "$native" "$ecm" "$doctools" "$work" "$CMAKE" "$NINJA" "$HOST_CC" "$HOST_CXX"; do
    case "$item" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2;; esac
    case "$item" in *[!a-zA-Z0-9_./+-]*) echo 'Use paths without shell/CMake metacharacters' >&2; exit 2;; esac
done
[ "$("$qt/bin/qmake" -query QT_VERSION)" = 6.12.0 ]
# HOST_DOCTOOLS is a prefix with devel/kf6-kdoctools-generators installed.
grep -q 'set(PACKAGE_VERSION "6.31.0")' "$doctools/lib/cmake/KF6DocTools/KF6DocToolsConfigVersion.cmake"
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
mkdir "$work"
mkdir "$work/source" "$work/tooling" "$work/tooling/KF6Package"
for component in kcoreaddons ki18n kpackage; do
    archive=$component-6.31.0.tar.xz
    expected=$(awk -F '\t' -v name="$archive" '$2 == name { print $3 }' "$root/sources.tsv")
    [ -n "$expected" ] && [ "$(shasum -a 256 "$distfiles/$archive" | awk '{print $1}')" = "$expected" ]
    printf '%s  %s\n' "$expected" "$archive" >> "$work/sources.sha256"
    tar -xf "$distfiles/$archive" -C "$work/source"
    if [ "$component" = kpackage ]; then
        # Same reviewed fixture corrections as the target recipe.
        patch -f -N -F 0 -p0 -d "$work/source/kpackage-6.31.0" < \
            "$root/../../../pkgsrc/devel/kf6-kpackage/patches/patch-autotests_appstream-fixtures"
    fi
    # These private host libraries serve the CLI metadata generator. QML and
    # scripted translations are not used by that CLI; target packages stay full.
    case "$component" in
        kcoreaddons) set -- -DKCOREADDONS_USE_QML=OFF ;;
        ki18n) set -- -DBUILD_WITH_QML=OFF ;;
        kpackage) set -- ;;
    esac
    "$CMAKE" -S "$work/source/$component-6.31.0" -B "$work/$component" -G Ninja \
        -DCMAKE_MAKE_PROGRAM="$NINJA" -DCMAKE_C_COMPILER="$HOST_CC" -DCMAKE_CXX_COMPILER="$HOST_CXX" \
        -DCMAKE_PREFIX_PATH="$work/prefix;$doctools;$qt;$native;${EXTRA_HOST_PREFIX:-}" \
        -DECM_DIR="$ecm" -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$work/prefix" \
        -DBUILD_TESTING=OFF -DCMAKE_EXPORT_COMPILE_COMMANDS=ON "$@" > "$work/$component-configure.log" 2>&1
    "$CMAKE" --build "$work/$component" --parallel "$JOBS" > "$work/$component-build.log" 2>&1
    "$CMAKE" --install "$work/$component" > "$work/$component-install.log" 2>&1
done
program=$work/prefix/bin/kpackagetool6
[ -x "$program" ]
"$program" --version > "$work/version.txt"
# Upstream reports CLI version 2.0; verify the actual library build version.
grep -qx '#define PACKAGE_VERSION_STRING "6.31.0"' "$work/kpackage/src/kpackage/kpackage_version.h"
sh "$root/tests/kpackage-metadata.sh" "$program" "$work/source/kpackage-6.31.0" "$work/metadata-check"
cat > "$work/tooling/KF6Package/KF6PackageToolsTargets.cmake" <<CMAKE
if(NOT TARGET KF6::kpackagetool6)
  add_executable(KF6::kpackagetool6 IMPORTED GLOBAL)
  set_target_properties(KF6::kpackagetool6 PROPERTIES IMPORTED_LOCATION "$program")
endif()
CMAKE
shasum -a 256 "$program" "$0" "$root/tests/kpackage-metadata.sh" \
    "$root/../../../pkgsrc/devel/kf6-kpackage/patches/patch-autotests_appstream-fixtures" > "$work/outputs.sha256"
"$CMAKE" --version > "$work/tool-versions.txt"
"$HOST_CXX" --version >> "$work/tool-versions.txt"
printf 'Built native KPackage tooling: %s\n' "$work/tooling"

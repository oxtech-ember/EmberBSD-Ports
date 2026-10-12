#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), current native documentation generators.
set -eu
[ "$#" = 5 ] || { echo 'Usage: build-doctools-host.sh DISTFILES HOST_QT NATIVE_PREFIX ECM_CMAKE_DIR NEW_WORK' >&2; exit 2; }
distfiles=$1 qt=$2 native=$3 ecm=$4 work=$5
: "${CMAKE:?Set native CMake}" "${NINJA:?Set native Ninja}" "${HOST_CC:?Set native C compiler}" "${HOST_CXX:?Set native C++ compiler}"
: "${JOBS:=2}"
for item in "$distfiles" "$qt" "$native" "$ecm" "$work" "$CMAKE" "$NINJA" "$HOST_CC" "$HOST_CXX"; do
    case "$item" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2;; esac
    case "$item" in *[!a-zA-Z0-9_./+-]*) echo 'Use paths without shell/CMake metacharacters' >&2; exit 2;; esac
done
[ "$("$qt/bin/qmake" -query QT_VERSION)" = 6.12.0 ]
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
mkdir "$work"
mkdir "$work/source" "$work/tooling" "$work/tooling/KF6DocTools"
for component in karchive kdoctools; do
    archive=$component-6.31.0.tar.xz
    expected=$(awk -F '\t' -v name="$archive" '$2 == name { print $3 }' "$root/sources.tsv")
    [ -n "$expected" ] && [ "$(shasum -a 256 "$distfiles/$archive" | awk '{print $1}')" = "$expected" ]
    tar -xf "$distfiles/$archive" -C "$work/source"
done
# These host-only libraries support the generators; target packages remain full.
"$CMAKE" -S "$work/source/karchive-6.31.0" -B "$work/archive" -G Ninja \
    -DCMAKE_MAKE_PROGRAM="$NINJA" -DCMAKE_C_COMPILER="$HOST_CC" -DCMAKE_CXX_COMPILER="$HOST_CXX" \
    -DCMAKE_PREFIX_PATH="$qt;$native" -DECM_DIR="$ecm" -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX="$work/prefix" -DBUILD_TESTING=OFF \
    > "$work/archive-configure.log" 2>&1
"$CMAKE" --build "$work/archive" --parallel "$JOBS" > "$work/archive-build.log" 2>&1
"$CMAKE" --install "$work/archive" > "$work/archive-install.log" 2>&1
# KI18n installs translations for the target package. The private host generators
# need no translated manuals; KArchive's cache-writing support stays enabled.
"$CMAKE" -S "$work/source/kdoctools-6.31.0" -B "$work/doctools" -G Ninja \
    -DCMAKE_MAKE_PROGRAM="$NINJA" -DCMAKE_C_COMPILER="$HOST_CC" -DCMAKE_CXX_COMPILER="$HOST_CXX" \
    -DCMAKE_PREFIX_PATH="$work/prefix;$qt;$native" -DECM_DIR="$ecm" -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX="$work/prefix" -DBUILD_TESTING=OFF \
    -DCMAKE_DISABLE_FIND_PACKAGE_KF6I18n=ON -DINSTALL_INTERNAL_TOOLS=ON \
    -DLIBXML2_XMLLINT_EXECUTABLE="$native/bin/xmllint" \
    -DDocBookXML4_DTD_DIR="$native/share/xml/docbook/4.5" \
    -DDOCBOOKXSL_DIR="$native/share/xsl/docbook" \
    > "$work/doctools-configure.log" 2>&1
"$CMAKE" --build "$work/doctools" --parallel "$JOBS" > "$work/doctools-build.log" 2>&1
"$CMAKE" --install "$work/doctools" > "$work/doctools-install.log" 2>&1
for program in meinproc6 checkXML6 docbookl10nhelper; do
    [ -x "$work/prefix/bin/$program" ]
    shasum -a 256 "$work/prefix/bin/$program" >> "$work/outputs.sha256"
done
"$work/prefix/bin/meinproc6" --version > "$work/version.txt"
# Upstream meinproc still reports its own hard-coded "5.0" tool version.
# Validate the configured Frameworks version instead of mislabelling that output.
grep -qx '#define KDOCTOOLS_VERSION_STRING "6.31.0"' "$work/doctools/src/kdoctools_version.h"
printf '6.31.0\n' > "$work/prefix/share/ember-doctools-version"
cat > "$work/tooling/KF6DocTools/KF6DocToolsToolsTargets.cmake" <<CMAKE
foreach(program meinproc6 checkXML6 docbookl10nhelper)
  if(NOT TARGET KF6::\${program})
    add_executable(KF6::\${program} IMPORTED)
    set_target_properties(KF6::\${program} PROPERTIES IMPORTED_LOCATION "$work/prefix/bin/\${program}")
  endif()
endforeach()
CMAKE
printf 'Built native KDocTools: %s\n' "$work/tooling"

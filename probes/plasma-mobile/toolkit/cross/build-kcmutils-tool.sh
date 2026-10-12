#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Build upstream native KCM metadata tooling.
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
archive=kcmutils-6.31.0.tar.xz
expected=$(awk -F '\t' '$1 == "devel/kf6-kcmutils" { print $3 }' "$toolkit/sources.tsv")
[ -n "$expected" ] && [ "$(shasum -a 256 "$distfiles/$archive" | awk '{print $1}')" = "$expected" ]
mkdir "$work"
mkdir "$work/source" "$work/tooling" "$work/tooling/KF6KCMUtils"
tar -xf "$distfiles/$archive" -C "$work/source"
# Native TOOLS_ONLY leaves the independent full target package unchanged.
"$CMAKE" -S "$work/source/kcmutils-6.31.0" -B "$work/build" -G Ninja \
    -DCMAKE_MAKE_PROGRAM="$NINJA" -DCMAKE_C_COMPILER="$HOST_CC" -DCMAKE_CXX_COMPILER="$HOST_CXX" \
    -DCMAKE_PREFIX_PATH="$qt" -DECM_DIR="$ecm" -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_TESTING=OFF -DTOOLS_ONLY=ON \
    -DQt6LinguistTools_DIR="$qt/lib/cmake/Qt6LinguistTools" > "$work/configure.log" 2>&1
"$CMAKE" --build "$work/build" --target kcmdesktopfilegenerator --parallel "$JOBS" > "$work/build.log" 2>&1
generator=$work/build/bin/kcmdesktopfilegenerator
if [ ! -x "$generator" ]; then
    generator=$generator.app/Contents/MacOS/kcmdesktopfilegenerator
fi
[ -x "$generator" ]
cat > "$work/kcm-fixture.json" <<'EOF'
{"KPlugin":{"Name":"Ember test","Name[ru]":"Проверка","Icon":"preferences-system"}}
EOF
"$generator" "$work/kcm-fixture.json" "$work/kcm-fixture.desktop"
grep -qx 'Exec=kcmshell6 kcm-fixture' "$work/kcm-fixture.desktop"
grep -qx 'Name=Ember test' "$work/kcm-fixture.desktop"
grep -Fx 'Name[ru]=Проверка' "$work/kcm-fixture.desktop"
if "$generator" "$work/missing.json" "$work/missing.desktop" > "$work/missing.log" 2>&1; then exit 1; fi
[ ! -e "$work/missing.desktop" ]
cat > "$work/tooling/KF6KCMUtils/KF6KCMUtilsToolingTargets.cmake" <<EOF
# Native build tool only; do not expose host target libraries to consumers.
if(NOT TARGET KF6::kcmdesktopfilegenerator)
add_executable(KF6::kcmdesktopfilegenerator IMPORTED GLOBAL)
set_target_properties(KF6::kcmdesktopfilegenerator PROPERTIES
  IMPORTED_LOCATION "$generator")
endif()
EOF
shasum -a 256 "$0" "$distfiles/$archive" "$generator" > "$work/inputs-output.sha256"
file "$generator" > "$work/architecture.txt"
printf 'Built KF6_HOST_TOOLING=%s\n' "$work/tooling"

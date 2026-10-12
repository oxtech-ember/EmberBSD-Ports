#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Qt sources retain their upstream licenses.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 DISTFILES NEW_ABSOLUTE_WORK" >&2; exit 2; }
distfiles=$1 work=$2
RESUME=${RESUME:-0}
: "${CMAKE:?Set an absolute native CMake executable}"
: "${NINJA:?Set an absolute native Ninja executable}"
: "${WAYLAND_SCANNER:?Set the matching native Wayland scanner}"
: "${HOST_LLVM_BUILD:?Set the completed native LLVM 23.1.3 build}"
: "${HOST_CLANG_BUILD:?Set the completed native Clang 23.1.3 build}"
HOST_CC=${HOST_CC:-/usr/bin/cc}
HOST_CXX=${HOST_CXX:-/usr/bin/c++}
JOBS=${JOBS:-2}
case "$JOBS" in ''|*[!0-9]*|0) echo 'JOBS must be positive' >&2; exit 2;; esac
for path in "$distfiles" "$work" "$CMAKE" "$NINJA" "$WAYLAND_SCANNER" "$HOST_CC" "$HOST_CXX" "$HOST_LLVM_BUILD" "$HOST_CLANG_BUILD"; do
    case "$path" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2;; esac
    case "$path" in *[!a-zA-Z0-9_./+-]*) echo 'Use paths without shell metacharacters' >&2; exit 2;; esac
done
for tool in "$CMAKE" "$NINJA" "$WAYLAND_SCANNER" "$HOST_CC" "$HOST_CXX"; do
    [ -x "$tool" ] || { echo "Missing executable: $tool" >&2; exit 2; }
done
[ "$("$WAYLAND_SCANNER" --version 2>&1)" = 'wayland-scanner 1.26.0' ]
[ "$("$HOST_LLVM_BUILD/bin/llvm-config" --version)" = 23.1.3 ]
[ -s "$HOST_CLANG_BUILD/lib/libclang.dylib" ]
[ -s "$HOST_CLANG_BUILD/lib/libclangHandleCXX.a" ]
[ -f "$HOST_CLANG_BUILD/lib/cmake/clang/ClangConfig.cmake" ]
if [ -e "$work" ] || [ -L "$work" ]; then
    [ "$RESUME" = 1 ] && [ ! -L "$work" ] && [ -f "$work/inputs.txt" ] || {
        echo 'Output already exists; resume only a build created by this recipe' >&2; exit 2;
    }
    for tool in "$CMAKE" "$NINJA" "$WAYLAND_SCANNER" "$HOST_CC" "$HOST_CXX"; do
        shasum -a 256 "$tool" | grep -F -x -f - "$work/inputs.txt" >/dev/null || {
            echo "Host input changed; use a new work directory: $tool" >&2; exit 2;
        }
    done
else
    [ "$RESUME" = 0 ] || { echo 'Cannot resume missing work' >&2; exit 2; }
fi
toolkit=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
modules='qtbase qtsvg qtshadertools qtdeclarative qttools qtquicktimeline qtquick3d'
for module in $modules; do
    archive=$module-everywhere-src-6.12.0.tar.xz
    expected=$(awk -F '\t' -v a="$archive" '$2 == a { print $3 }' "$toolkit/sources.tsv")
    [ -n "$expected" ] && [ "$(shasum -a 256 "$distfiles/$archive" | awk '{print $1}')" = "$expected" ] || {
        echo "Archive verification failed: $archive" >&2; exit 2;
    }
done
mkdir -p "$work"
mkdir -p "$work/source" "$work/bin"
ln -sf "$CMAKE" "$work/bin/cmake"
ln -sf "$NINJA" "$work/bin/ninja"
PATH="$work/bin:$PATH"
export PATH
{
    shasum -a 256 "$0" "$toolkit/sources.tsv" "$CMAKE" "$NINJA" "$WAYLAND_SCANNER" "$HOST_CC" "$HOST_CXX"
    "$CMAKE" --version
    "$NINJA" --version
    shasum -a 256 "$HOST_LLVM_BUILD/lib/cmake/llvm/LLVMConfig.cmake" \
        "$HOST_CLANG_BUILD/lib/cmake/clang/ClangConfig.cmake" \
        "$HOST_CLANG_BUILD/lib/libclang.dylib"
    "$HOST_CC" --version
} >> "$work/inputs.txt"
for module in $modules; do
    archive=$module-everywhere-src-6.12.0.tar.xz
    shasum -a 256 "$distfiles/$archive" >> "$work/inputs.txt"
    if [ ! -d "$work/source/$module-everywhere-src-6.12.0" ]; then
        tar -xf "$distfiles/$archive" -C "$work/source"
    fi
    mkdir -p "$work/$module"
    for log in configure build; do
        if [ -f "$work/$module/$log.log" ]; then
            mv "$work/$module/$log.log" "$work/$module/$log.before-resume-$$.log"
        fi
    done
    if [ "$module" = qtbase ]; then
        # Find the portable XML generator on macOS too. Do this at initial
        # configure: developer builds cache failed package searches.
        (cd "$work/$module" && CC="$HOST_CC" CXX="$HOST_CXX" \
            "$work/source/$module-everywhere-src-6.12.0/configure" \
            -developer-build -opensource -confirm-license -release \
            -nomake tests -nomake examples -- \
            -DCMAKE_MAKE_PROGRAM="$NINJA" -DQT_FIND_ALL_PACKAGES_ALWAYS=ON \
            -DWaylandScanner_EXECUTABLE="$WAYLAND_SCANNER" \
            -DFEATURE_qtwaylandscanner=ON) > "$work/$module/configure.log" 2>&1
        # Other modules' host generators link these libraries. Their metadata
        # alone is insufficient when the modules are built independently.
        "$CMAKE" --build "$work/$module" --parallel "$JOBS" \
            --target host_tools Gui Network Widgets OpenGL Sql Concurrent Test QMinimalIntegrationPlugin \
            > "$work/$module/build.log" 2>&1
    else
        set --
        [ "$module" != qtdeclarative ] || set -- -DFEATURE_quick_vectorimage=ON
        if [ "$module" = qttools ]; then
            set -- -DLLVM_DIR="$HOST_LLVM_BUILD/lib/cmake/llvm" \
                -DClang_DIR="$HOST_CLANG_BUILD/lib/cmake/clang" \
                -DFEATURE_clang=ON -DFEATURE_qdoc=ON
            # Upstream macOS archives contain LLVM 23 LTO bitcode. Apple ld's
            # bundled older reader cannot decode it; select the matching plugin.
            if [ "$(uname -s)" = Darwin ] && [ -s "$HOST_LLVM_BUILD/lib/libLTO.dylib" ]; then
                set -- "$@" "-DCMAKE_EXE_LINKER_FLAGS=-Wl,-lto_library,$HOST_LLVM_BUILD/lib/libLTO.dylib"
                shasum -a 256 "$HOST_LLVM_BUILD/lib/libLTO.dylib" >> "$work/inputs.txt"
            fi
        fi
        (cd "$work/$module" && "$work/qtbase/bin/qt-configure-module" \
            "$work/source/$module-everywhere-src-6.12.0" \
            -- -DQT_BUILD_TESTS=OFF -DQT_BUILD_EXAMPLES=OFF "$@") > "$work/$module/configure.log" 2>&1
        target=host_tools
        [ "$module" != qtsvg ] || target=Svg
        [ "$module" != qtquicktimeline ] || target=QuickTimeline
        set -- "$target"
        # balsam's executable alone cannot import assets without this plugin.
        [ "$module" != qtquick3d ] || set -- host_tools AssimpImporterPlugin
        "$CMAKE" --build "$work/$module" --parallel "$JOBS" --target "$@" \
            > "$work/$module/build.log" 2>&1
    fi
done
[ "$("$work/qtbase/bin/qmake" -query QT_VERSION)" = 6.12.0 ]
for tool in moc rcc uic qtwaylandscanner qmlcachegen qmltyperegistrar; do
    [ -x "$work/qtbase/libexec/$tool" ] || { echo "Missing host tool: $tool" >&2; exit 1; }
done
for tool in qsb lrelease svgtoqml qdoc; do
    [ -x "$work/qtbase/bin/$tool" ] || { echo "Missing host tool: $tool" >&2; exit 1; }
done
(cd "$work/qtbase" && find bin libexec plugins/assetimporters -type f -exec shasum -a 256 {} \;) > "$work/tools.sha256"
printf 'Built Qt 6.12 host tools: %s\n' "$work/qtbase"

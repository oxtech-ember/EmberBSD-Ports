#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Qt sources retain their upstream licenses.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 DISTFILES NEW_ABSOLUTE_WORK" >&2; exit 2; }
distfiles=$1 work=$2
profile=${QT_HOST_TOOLS_PROFILE:-full}
plan_only=${QT_HOST_TOOLS_PLAN_ONLY:-0}
case "$profile" in
full) modules='qtbase qtsvg qtshadertools qtdeclarative qttools qtquicktimeline qtquick3d' ;;
quick) modules='qtbase qtsvg qtshadertools qtdeclarative' ;;
*) echo "Invalid QT_HOST_TOOLS_PROFILE: $profile" >&2; exit 2 ;;
esac
case "$plan_only" in 0|1) ;; *) echo 'QT_HOST_TOOLS_PLAN_ONLY must be 0 or 1' >&2; exit 2;; esac
toolkit=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
scanner_patch=$toolkit/../../../pkgsrc/x11/qt6-qtbase/patches/patch-src_tools_qtwaylandscanner_qtwaylandscanner.cpp
RESUME=${RESUME:-0}
: "${CMAKE:?Set an absolute native CMake executable}"
: "${NINJA:?Set an absolute native Ninja executable}"
: "${TAR:?Set an absolute native tar executable}"
: "${PATCH:?Set an absolute native patch executable}"
: "${HOST_PYTHON:?Set an absolute native Python 3 executable}"
: "${WAYLAND_SCANNER:?Set the matching native Wayland scanner}"
qdoc_paths=
if [ "$profile" = full ]; then
    : "${HOST_LLVM_BUILD:?Set the completed native LLVM 23.1.4 build}"
    : "${HOST_CLANG_BUILD:?Set the completed native Clang 23.1.4 build}"
    qdoc_paths="$HOST_LLVM_BUILD $HOST_CLANG_BUILD"
fi
: "${HOST_DBUS_PREFIX:?Set the native D-Bus prefix with headers, library and DBus1 CMake exports}"
: "${HOST_CC:?Set the selected native C compiler}"
: "${HOST_CXX:?Set the selected native C++ compiler}"
JOBS=${JOBS:-2}
case "$JOBS" in ''|*[!0-9]*|0) echo 'JOBS must be positive' >&2; exit 2;; esac
for path in "$distfiles" "$work" "$CMAKE" "$NINJA" "$TAR" "$PATCH" "$HOST_PYTHON" "$WAYLAND_SCANNER" "$HOST_CC" "$HOST_CXX" "$HOST_DBUS_PREFIX" $qdoc_paths; do
    case "$path" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2;; esac
    case "$path" in *[!a-zA-Z0-9_./+-]*) echo 'Use paths without shell metacharacters' >&2; exit 2;; esac
done
for tool in "$CMAKE" "$NINJA" "$TAR" "$PATCH" "$HOST_PYTHON" "$WAYLAND_SCANNER" "$HOST_CC" "$HOST_CXX"; do
    [ -x "$tool" ] || { echo "Missing executable: $tool" >&2; exit 2; }
done
# Interrupted extraction must not make an unpatched tree resumable.
if [ "$RESUME" = 1 ] && [ -d "$work/source/qtbase-everywhere-src-6.12.0" ]; then
    [ -f "$work/qtbase-scanner-source.sha256" ] || {
        echo 'Missing patched Qt scanner proof; use a new work directory.' >&2; exit 2;
    }
fi
[ "$("$WAYLAND_SCANNER" --version 2>&1)" = 'wayland-scanner 1.26.0' ]
# QtCore uses the CMake archive API with Zstandard. Check before work starts.
zstd_probe=$(mktemp -d "${TMPDIR:-/tmp}/ember-cmake-zstd.XXXXXXXX")
: > "$zstd_probe/empty"
if ! (cd "$zstd_probe" && "$CMAKE" -E tar cf probe.tar.zst --zstd empty) > "$zstd_probe/log" 2>&1; then
    rm -rf "$zstd_probe"
    echo 'CMAKE must support Zstandard archives; see README.md' >&2
    exit 2
fi
rm -rf "$zstd_probe"
if [ "$profile" = full ]; then
    [ "$("$HOST_LLVM_BUILD/bin/llvm-config" --version)" = 23.1.4 ]
    case "$(uname -s)" in
    Darwin) host_clang_library=$HOST_CLANG_BUILD/lib/libclang.dylib ;;
    *) host_clang_library=$HOST_CLANG_BUILD/lib/libclang.so ;;
    esac
    [ -s "$host_clang_library" ]
    [ -s "$HOST_CLANG_BUILD/lib/libclangHandleCXX.a" ]
    [ -f "$HOST_CLANG_BUILD/lib/cmake/clang/ClangConfig.cmake" ]
fi
# Complex D-Bus type signatures require the real native libdbus marshaller.
# Lazy loading can silently emit empty XML types on hosts without a default path.
case "$(uname -s)" in
Darwin) host_dbus_library=$HOST_DBUS_PREFIX/lib/libdbus-1.dylib ;;
*) host_dbus_library=$HOST_DBUS_PREFIX/lib/libdbus-1.so ;;
esac
host_dbus_inputs="$HOST_DBUS_PREFIX/lib/cmake/DBus1/DBus1Config.cmake $HOST_DBUS_PREFIX/lib/cmake/DBus1/DBus1ConfigVersion.cmake $HOST_DBUS_PREFIX/lib/pkgconfig/dbus-1.pc $host_dbus_library $HOST_DBUS_PREFIX/include/dbus-1.0/dbus/dbus.h $HOST_DBUS_PREFIX/lib/dbus-1.0/include/dbus/dbus-arch-deps.h"
for input in $host_dbus_inputs; do
    [ -s "$input" ] || { echo "Missing native D-Bus input: $input" >&2; exit 2; }
done
if [ -e "$work" ] || [ -L "$work" ]; then
    [ "$RESUME" = 1 ] && [ ! -L "$work" ] && [ -f "$work/inputs.txt" ] || {
        echo 'Output already exists; resume only a build created by this recipe' >&2; exit 2;
    }
    grep -q -x "profile=$profile" "$work/inputs.txt" || {
        echo 'Host profile changed; use a new work directory' >&2; exit 2;
    }
    for tool in "$0" "$toolkit/sources.tsv" "$CMAKE" "$NINJA" "$TAR" "$PATCH" "$HOST_PYTHON" "$WAYLAND_SCANNER" "$HOST_CC" "$HOST_CXX" "$scanner_patch" $host_dbus_inputs; do
        shasum -a 256 "$tool" | grep -F -x -f - "$work/inputs.txt" >/dev/null || {
            echo "Host input changed; use a new work directory: $tool" >&2; exit 2;
        }
    done
else
    [ "$RESUME" = 0 ] || { echo 'Cannot resume missing work' >&2; exit 2; }
fi
for module in $modules; do
    archive=$module-everywhere-src-6.12.0.tar.xz
    expected=$(awk -F '\t' -v a="$archive" '$2 == a { print $3 }' "$toolkit/sources.tsv")
    [ -n "$expected" ] && [ "$(shasum -a 256 "$distfiles/$archive" | awk '{print $1}')" = "$expected" ] || {
        echo "Archive verification failed: $archive" >&2; exit 2;
    }
done
if [ "$plan_only" = 1 ]; then
    modules_csv=$(printf '%s' "$modules" | tr ' ' ',')
    printf 'PLAN: profile=%s modules=%s\n' "$profile" "$modules_csv"
    exit 0
fi
mkdir -p "$work"
mkdir -p "$work/source" "$work/bin"
ln -sf "$CMAKE" "$work/bin/cmake"
ln -sf "$NINJA" "$work/bin/ninja"
PATH="$work/bin:$PATH"
export PATH
{
    shasum -a 256 "$0" "$toolkit/sources.tsv" "$CMAKE" "$NINJA" "$TAR" "$PATCH" "$HOST_PYTHON" "$WAYLAND_SCANNER" "$HOST_CC" "$HOST_CXX" "$scanner_patch" $host_dbus_inputs
    "$CMAKE" --version
    "$NINJA" --version
    printf 'profile=%s\n' "$profile"
    if [ "$profile" = full ]; then
        shasum -a 256 "$HOST_LLVM_BUILD/lib/cmake/llvm/LLVMConfig.cmake" \
            "$HOST_CLANG_BUILD/lib/cmake/clang/ClangConfig.cmake" \
            "$host_clang_library"
    fi
    "$HOST_CC" --version
} >> "$work/inputs.txt"
for module in $modules; do
    archive=$module-everywhere-src-6.12.0.tar.xz
    shasum -a 256 "$distfiles/$archive" >> "$work/inputs.txt"
    if [ ! -d "$work/source/$module-everywhere-src-6.12.0" ]; then
        "$TAR" -xf "$distfiles/$archive" -C "$work/source"
        if [ "$module" = qtbase ]; then
            "$PATCH" -d "$work/source/$module-everywhere-src-6.12.0" -p0 -F0 -i "$scanner_patch"
            (cd "$work/source/$module-everywhere-src-6.12.0" &&
                shasum -a 256 src/tools/qtwaylandscanner/qtwaylandscanner.cpp > "$work/qtbase-scanner-source.sha256")
        fi
    fi
    mkdir -p "$work/$module"
    for log in configure build; do
        if [ -f "$work/$module/$log.log" ]; then
            mv "$work/$module/$log.log" "$work/$module/$log.before-resume-$$.log"
        fi
    done
    if [ "$module" = qtbase ]; then
        [ -f "$work/qtbase-scanner-source.sha256" ] &&
            (cd "$work/source/$module-everywhere-src-6.12.0" &&
                shasum -a 256 -c "$work/qtbase-scanner-source.sha256") || {
            echo 'Patched Qt scanner source proof failed; use a new work directory.' >&2; exit 2;
        }
        # Find the portable XML generator on macOS too. Do this at initial
        # configure: developer builds cache failed package searches.
        (cd "$work/$module" && CC="$HOST_CC" CXX="$HOST_CXX" \
            "$work/source/$module-everywhere-src-6.12.0/configure" \
            -developer-build -opensource -confirm-license -release \
            -nomake tests -nomake examples -- \
            -DCMAKE_MAKE_PROGRAM="$NINJA" -DPython3_EXECUTABLE:FILEPATH="$HOST_PYTHON" -DQT_FIND_ALL_PACKAGES_ALWAYS=ON \
            -UQT_INTERNAL_PREVIOUSLY_FOUND_PACKAGES \
            -UQT_INTERNAL_PREVIOUSLY_SEARCHED_PACKAGES \
            -DDBus1_DIR="$HOST_DBUS_PREFIX/lib/cmake/DBus1" \
            -DDBus1_LIBRARY:FILEPATH="$host_dbus_library" \
            -DDBus1_INCLUDE_DIR:PATH="$HOST_DBUS_PREFIX/include/dbus-1.0" \
            -DDBus1_ARCH_INCLUDE_DIR:PATH="$HOST_DBUS_PREFIX/lib/dbus-1.0/include" \
            -DFEATURE_dbus=ON -DFEATURE_dbus_linked=ON \
            -DWaylandScanner_EXECUTABLE="$WAYLAND_SCANNER" \
            -DFEATURE_qtwaylandscanner=ON) > "$work/$module/configure.log" 2>&1
        # Qt can reset a requested feature when a dependency search was cached.
        # Reject that result before an XML generator can emit empty signatures.
        grep -q -x 'FEATURE_dbus_linked:BOOL=ON' "$work/$module/CMakeCache.txt"
        grep -q -x 'QT_FEATURE_dbus_linked:INTERNAL=ON' "$work/$module/CMakeCache.txt"
        # Other modules' host generators link these libraries. Their metadata
        # alone is insufficient when the modules are built independently.
        "$CMAKE" --build "$work/$module" --parallel "$JOBS" \
            --target host_tools Gui Network Widgets OpenGL Sql Concurrent Test PrintSupport QSQLiteDriverPlugin QMinimalIntegrationPlugin \
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
            -- -DQT_BUILD_TESTS=OFF -DQT_BUILD_EXAMPLES=OFF -DPython3_EXECUTABLE:FILEPATH="$HOST_PYTHON" "$@") > "$work/$module/configure.log" 2>&1
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
required_tools='qsb svgtoqml qdbuscpp2xml qdbusxml2cpp'
[ "$profile" != full ] || required_tools="$required_tools lrelease qdoc balsam"
for tool in $required_tools; do
    [ -x "$work/qtbase/bin/$tool" ] || { echo "Missing host tool: $tool" >&2; exit 1; }
done
inventory_paths='bin libexec'
[ "$profile" != full ] || inventory_paths="$inventory_paths plugins/assetimporters"
(cd "$work/qtbase" && find $inventory_paths -type f -exec shasum -a 256 {} \;) > "$work/tools.sha256"
printf 'Built Qt 6.12 host tools (%s): %s\n' "$profile" "$work/qtbase"

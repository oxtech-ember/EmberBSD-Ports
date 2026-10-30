#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Qt sources retain their upstream licenses.
set -eu
[ "${QT_HOST_LOCKED:-}" = 1 ] || { echo "Use run-host-tools.py to hold the SDK host work lock" >&2; exit 2; }
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
syncqt_patch=$toolkit/../../../pkgsrc/x11/qt6-qtbase/patches/patch-src_tools_syncqt_CMakeLists.txt
zlib_patch=$toolkit/../../../pkgsrc/x11/qt6-qtbase/patches/patch-cmake_FindWrapSystemZLIB.cmake
widgets_patch=$toolkit/../../../pkgsrc/x11/qt6-qtbase/patches/patch-src_widgets_CMakeLists.txt
markdown_patch=$toolkit/../../../pkgsrc/x11/qt6-qtbase/patches/patch-src_gui_text_qtextmarkdownimporter.cpp
shader_patches="$toolkit/../../../pkgsrc/graphics/qt6-qtshadertools/patches/patch-src_CMakeLists.txt $toolkit/../../../pkgsrc/graphics/qt6-qtshadertools/patches/patch-src_shadertools_CMakeLists.txt $toolkit/../../../pkgsrc/graphics/qt6-qtshadertools/patches/patch-src_shadertools_qspirvcompiler.cpp $toolkit/../../../pkgsrc/graphics/qt6-qtshadertools/patches/patch-src_shadertools_qspirvshaderremap.cpp $toolkit/../../../pkgsrc/graphics/qt6-qtshadertools/patches/patch-src_shadertools_qspirvshaderremap_p.h"
quick3d_patches="$toolkit/../../../pkgsrc/graphics/qt6-qtquick3d/patches/patch-src_3rdparty_CMakeLists.txt $toolkit/../../../pkgsrc/graphics/qt6-qtquick3d/patches/patch-src_runtimerender_CMakeLists.txt $toolkit/../../../pkgsrc/graphics/qt6-qtquick3d/patches/patch-src_runtimerender_rendererimpl_qssglightmapper.cpp $toolkit/../../../pkgsrc/graphics/qt6-qtquick3d/patches/patch-src_runtimerender_resourcemanager_qssgrenderloadedtexture.cpp $toolkit/../../../pkgsrc/graphics/qt6-qtquick3d/patches/patch-src_utils_CMakeLists.txt"
qttools_patch=$toolkit/../../../pkgsrc/devel/qt6-qttools/patches/patch-src_linguist_Qt6LinguistToolsMacros.cmake
qtbase_network_patches="$toolkit/../../../pkgsrc/x11/qt6-qtbase/patches/patch-src_network_CMakeLists.txt $toolkit/../../../pkgsrc/x11/qt6-qtbase/patches/patch-src_network_configure.cmake $toolkit/../../../pkgsrc/x11/qt6-qtbase/patches/patch-src_network_kernel_qtldurl.cpp"
quick3d_transition=$toolkit/cross/qt-source-transition.py
quick3d_inputs=
[ "$profile" != full ] || quick3d_inputs="$quick3d_patches $quick3d_transition $toolkit/cross/check-quick3d-cache.py"
RESUME=${RESUME:-0}
HOST_INCREMENTAL_RECONFIGURE=${HOST_INCREMENTAL_RECONFIGURE:-0}
case "$HOST_INCREMENTAL_RECONFIGURE" in
0) ;;
1) [ "$RESUME" = 1 ] || { echo 'Incremental reconfigure requires RESUME=1' >&2; exit 2; } ;;
*) echo 'HOST_INCREMENTAL_RECONFIGURE must be 0 or 1' >&2; exit 2 ;;
esac
HOST_SH=${HOST_SH:-/bin/sh}
HOST_RUNTIME_VIEW=${HOST_RUNTIME_VIEW:-}
QT_HOST_RESUME_FROM=${QT_HOST_RESUME_FROM:-}
HOST_QT_QUICK3D_BUILD_DIR=${HOST_QT_QUICK3D_BUILD_DIR:-$work/qtquick3d}
case "$QT_HOST_RESUME_FROM" in
'') ;;
qtquick3d|qttools|qtbase-network|qtbase-xml) [ "$RESUME" = 1 ] && [ "$HOST_INCREMENTAL_RECONFIGURE" = 1 ] && [ "$profile" = full ] || {
    echo 'Selected module resume requires full incremental reconfigure' >&2; exit 2; } ;;
*) echo 'Unsupported Qt host resume starting module' >&2; exit 2 ;;
esac
: "${HOST_PYTHON:?Set an absolute native Python 3 executable}"
runtime_inputs=
runtime_view_identity=none
if [ -n "$HOST_RUNTIME_VIEW" ]; then
    [ "$(uname -s)" = Darwin ] || { echo 'Native runtime view requires Darwin' >&2; exit 2; }
    : "${HOST_SDK_SOURCE:?Set the SDK source for the selected native runtime}"
    for path in "$HOST_RUNTIME_VIEW" "$HOST_SDK_SOURCE"; do
        case "$path" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2;; esac
        case "$path" in *[!a-zA-Z0-9_./+-]*) echo 'Use paths without shell metacharacters' >&2; exit 2;; esac
    done
    [ -d "$HOST_RUNTIME_VIEW" ] || { echo 'Native runtime view is not a directory' >&2; exit 2; }
    runtime_launcher=$HOST_SDK_SOURCE/scripts/run-darwin-with-runtime.py
    runtime_module=$HOST_SDK_SOURCE/src/emberbsd_sdk/runtime_loader.py
    runtime_cmake=$toolkit/cross/native-host-runtime.cmake
    for input in "$runtime_launcher" "$runtime_module" "$runtime_cmake"; do
        [ -s "$input" ] || { echo "Missing native runtime input: $input" >&2; exit 2; }
        runtime_inputs="$runtime_inputs $input"
    done
    for input in "$HOST_RUNTIME_VIEW"/*; do
        [ -f "$input" ] || { echo 'Native runtime view contains a missing or non-file entry' >&2; exit 2; }
        case "$input" in *[!a-zA-Z0-9_./+-]*) echo 'Use paths without shell metacharacters' >&2; exit 2;; esac
        runtime_inputs="$runtime_inputs $input"
    done
    runtime_view_identity=$(shasum -a 256 "$HOST_RUNTIME_VIEW"/* | shasum -a 256 | cut -d ' ' -f 1)
    QT_NATIVE_RUNTIME_PYTHON=$HOST_PYTHON QT_NATIVE_RUNTIME_LAUNCHER=$runtime_launcher QT_NATIVE_RUNTIME_VIEW=$HOST_RUNTIME_VIEW
    export QT_NATIVE_RUNTIME_PYTHON QT_NATIVE_RUNTIME_LAUNCHER QT_NATIVE_RUNTIME_VIEW
fi
: "${CMAKE:?Set an absolute native CMake executable}"
: "${NINJA:?Set an absolute native Ninja executable}"
: "${TAR:?Set an absolute native tar executable}"
: "${PATCH:?Set an absolute native patch executable}"
: "${WAYLAND_SCANNER:?Set the matching native Wayland scanner}"
qdoc_paths=
if [ "$profile" = full ]; then
    : "${HOST_LLVM_BUILD:?Set the completed native LLVM 23.1.4 build}"
    : "${HOST_CLANG_BUILD:?Set the completed native Clang 23.1.4 build}"
    qdoc_paths="$HOST_LLVM_BUILD $HOST_CLANG_BUILD"
fi
: "${HOST_DBUS_PREFIX:?Set the native D-Bus prefix with headers, library and DBus1 CMake exports}"
: "${HOST_PACKAGE_PREFIX:?Set the selected native dependency prefix}"
: "${HOST_PKG_CONFIG:?Set the selected native pkg-config executable}"
resume_otool_input=
[ -z "$HOST_RUNTIME_VIEW" ] || resume_otool_input=$HOST_PACKAGE_PREFIX/bin/llvm-otool
: "${HOST_CC:?Set the selected native C compiler}"
: "${HOST_CXX:?Set the selected native C++ compiler}"
JOBS=${JOBS:-2}
case "$JOBS" in ''|*[!0-9]*|0) echo 'JOBS must be positive' >&2; exit 2;; esac
for path in "$toolkit" "$distfiles" "$work" "$HOST_SH" "$CMAKE" "$NINJA" "$TAR" "$PATCH" "$HOST_PYTHON" "$WAYLAND_SCANNER" "$HOST_CC" "$HOST_CXX" "$HOST_DBUS_PREFIX" "$HOST_PACKAGE_PREFIX" "$HOST_PKG_CONFIG" $qdoc_paths; do
    case "$path" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2;; esac
    case "$path" in *[!a-zA-Z0-9_./+-]*) echo 'Use paths without shell metacharacters' >&2; exit 2;; esac
done
for tool in "$HOST_SH" "$CMAKE" "$NINJA" "$TAR" "$PATCH" "$HOST_PYTHON" "$WAYLAND_SCANNER" "$HOST_CC" "$HOST_CXX" "$HOST_PKG_CONFIG"; do
    [ -x "$tool" ] || { echo "Missing executable: $tool" >&2; exit 2; }
done
host_deployment_target=
host_darwin_sdk=
host_codesign=
if [ "$(uname -s)" = Darwin ]; then
    # Qt's macOS test runner uses the operating system signing service.
    host_codesign=${HOST_CODESIGN:-/usr/bin/codesign}
    case "$host_codesign" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2;; esac
    case "$host_codesign" in *[!a-zA-Z0-9_./+-]*) echo 'Use paths without shell metacharacters' >&2; exit 2;; esac
    [ -x "$host_codesign" ] || { echo "Missing executable: $host_codesign" >&2; exit 2; }
    : "${HOST_DARWIN_SDK:?Set the Darwin SDK selected by the native compiler binding}"
    host_darwin_sdk=$HOST_DARWIN_SDK
    case "$host_darwin_sdk" in /*) ;; *) echo 'Absolute Darwin SDK path required' >&2; exit 2;; esac
    case "$host_darwin_sdk" in *[!a-zA-Z0-9_./+-]*) echo 'Use a Darwin SDK path without shell metacharacters' >&2; exit 2;; esac
    [ -d "$host_darwin_sdk/System/Library/Frameworks" ] && [ -s "$host_darwin_sdk/usr/include/cups/cups.h" ] && [ -s "$host_darwin_sdk/usr/lib/libcups.tbd" ] || { echo 'Selected Darwin SDK lacks platform frameworks or printing ABI' >&2; exit 2; }
    "$HOST_CC" -### -x c -c /dev/null 2>&1 | grep -F -- "$host_darwin_sdk" >/dev/null || { echo 'Native compiler does not select the requested Darwin SDK' >&2; exit 2; }
    : "${HOST_MACOSX_DEPLOYMENT_TARGET:?Set the deployment target selected by the native compiler binding}"
    host_deployment_target=$HOST_MACOSX_DEPLOYMENT_TARGET
    case "$host_deployment_target" in *[!0-9.]*|.*|*.|*..*|'') echo 'Invalid native deployment target' >&2; exit 2;; esac
    printf 'int main() { return 0; }\n' | "$HOST_CXX" "-mmacosx-version-min=$host_deployment_target" -x c++ -fsyntax-only - || {
        echo 'Native compiler rejects deployment target' >&2; exit 2;
    }
fi
# Interrupted extraction must not make an unpatched tree resumable.
if [ "$RESUME" = 1 ] && [ -d "$work/source/qtbase-everywhere-src-6.12.0" ]; then
    [ -f "$work/qtbase-scanner-source.sha256" ] || {
        echo 'Missing patched Qt scanner proof; use a new work directory.' >&2; exit 2;
    }
fi
if [ "$RESUME" = 1 ] && [ -d "$work/source/qtshadertools-everywhere-src-6.12.0" ]; then
    [ -f "$work/qtshadertools-source.sha256" ] || {
        echo 'Missing patched Qt ShaderTools proof; use a new work directory.' >&2; exit 2;
    }
    (cd "$work/source/qtshadertools-everywhere-src-6.12.0" && shasum -a 256 -c "$work/qtshadertools-source.sha256") || {
        echo 'Patched Qt ShaderTools source proof failed; use a new work directory.' >&2; exit 2;
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
    resume_helper=$toolkit/cross/host-resume-inputs.py
    [ -f "$resume_helper" ] || { echo 'Missing Qt host resume checker' >&2; exit 2; }
    resume_record=$("$HOST_PYTHON" -I "$resume_helper" "$work/inputs.txt" "$toolkit/cross/build-host-tools.sh" \
        "$HOST_RUNTIME_VIEW" "$profile" "$HOST_PACKAGE_PREFIX" "$host_deployment_target" "$work" "$HOST_DBUS_PREFIX" "$resume_otool_input" "$HOST_INCREMENTAL_RECONFIGURE") || exit 2
    set -- $resume_record
    [ "$#" = 2 ] || { echo 'Invalid Qt host resume result' >&2; exit 2; }
    old_producer_identity=$1 resume_start=$2
    old_producer_path=$(sed -n "${resume_start}p" "$work/inputs.txt" | cut -c 67-)
    old_toolkit=${old_producer_path%/cross/build-host-tools.sh}
    # The predecessor did not record this checker. Later builds must retain it.
    resume_extra_inputs=
    case "$old_producer_identity" in
    2987bc8a260733ebcec67eeda99d1da40488a40fb4493fda76e37a3a28ebd329|4ec29e9a317a7b794b4f5de60dd940065a3c034bf1c8230df92163eb9fe6ac67) ;;
    *) resume_extra_inputs="$resume_helper $resume_otool_input" ;;
    esac
    if [ "$HOST_INCREMENTAL_RECONFIGURE" = 1 ] && [ -n "$resume_extra_inputs" ]; then
        resume_extra_inputs=$resume_otool_input
    fi
    if [ "$profile" = full ]; then
        resume_full_inputs="$HOST_LLVM_BUILD/lib/cmake/llvm/LLVMConfig.cmake $HOST_CLANG_BUILD/lib/cmake/clang/ClangConfig.cmake $host_clang_library"
    else
        resume_full_inputs=
    fi
    for tool in "$toolkit/sources.tsv" "$HOST_SH" "$CMAKE" "$NINJA" "$TAR" "$PATCH" "$HOST_PYTHON" "$WAYLAND_SCANNER" "$HOST_CC" "$HOST_CXX" "$HOST_PKG_CONFIG" "$scanner_patch" "$syncqt_patch" "$zlib_patch" "$widgets_patch" "$markdown_patch" $shader_patches $host_dbus_inputs $runtime_inputs $host_codesign $resume_full_inputs $resume_extra_inputs; do
        # Incremental mode validates each selected Qt archive against both
        # the current manifest and the previous input block below.
        if [ "$HOST_INCREMENTAL_RECONFIGURE" = 1 ] && [ "$tool" = "$toolkit/sources.tsv" ]; then
            continue
        fi
        # An incremental configure may adopt the current owner runtime hook.
        # The selected SDK launcher and module remain strict inputs.
        if [ "$HOST_INCREMENTAL_RECONFIGURE" = 1 ] && [ -n "$HOST_RUNTIME_VIEW" ] && [ "$tool" = "$runtime_cmake" ]; then
            continue
        fi
        # The runtime view is compared by basename and digest by the checker.
        if [ -n "$HOST_RUNTIME_VIEW" ]; then
            case "$tool" in "$HOST_RUNTIME_VIEW"/*) continue ;; esac
        fi
        old_path=$tool
        # A different checkout is allowed only for an explicit incremental
        # reconfigure; the previous owner input must still match byte for byte.
        if [ "$HOST_INCREMENTAL_RECONFIGURE" = 1 ]; then
            case "$tool" in "$toolkit/"*) old_path=$old_toolkit/${tool#"$toolkit/"} ;; esac
        fi
        hash=$(shasum -a 256 "$tool" | cut -d ' ' -f 1)
        sed -n "${resume_start},\$p" "$work/inputs.txt" | grep -F -x "$hash  $old_path" >/dev/null || {
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
    if [ "$RESUME" = 1 ] && [ -d "$work/source/$module-everywhere-src-6.12.0" ]; then
        grep -F -x "$expected  $distfiles/$archive" "$work/inputs.txt" >/dev/null || {
            echo "Previous archive input changed: $archive" >&2; exit 2;
        }
    fi
done
if [ "$HOST_QT_QUICK3D_BUILD_DIR" != "$work/qtquick3d" ]; then
    [ "$QT_HOST_RESUME_FROM" = qtquick3d ] || { echo 'External Quick3D build requires selected module resume' >&2; exit 2; }
    case "$HOST_QT_QUICK3D_BUILD_DIR" in /*) ;; *) echo 'Quick3D build path must be absolute' >&2; exit 2;; esac
    case "$HOST_QT_QUICK3D_BUILD_DIR" in *[!a-zA-Z0-9_./+-]*) echo 'Use a Quick3D build path without shell metacharacters' >&2; exit 2;; esac
    "$HOST_PYTHON" -I "$toolkit/cross/check-quick3d-cache.py" \
        "$HOST_QT_QUICK3D_BUILD_DIR" "$work" "$HOST_PACKAGE_PREFIX" "$HOST_CC" "$HOST_CXX" \
        "$host_deployment_target" "${runtime_cmake:-}"

fi
if [ "$QT_HOST_RESUME_FROM" = qtquick3d ]; then
    for tool in libexec/moc libexec/rcc libexec/uic libexec/qmlcachegen bin/qsb bin/svgtoqml bin/lrelease bin/qdoc; do
        [ -x "$work/qtbase/$tool" ] || { echo "Missing previous Qt host tool: $tool" >&2; exit 2; }
    done
    for module in Core CoreTools Svg ShaderTools Qml LinguistTools QuickTimeline; do
        [ -s "$work/qtbase/lib/cmake/Qt6$module/Qt6${module}Config.cmake" ] || {
            echo "Missing previous Qt CMake package: $module" >&2; exit 2;
        }
    done
fi
if [ "$QT_HOST_RESUME_FROM" = qtbase-network ] || [ "$QT_HOST_RESUME_FROM" = qtbase-xml ]; then
    [ -x "$work/qtbase/libexec/moc" ] && [ -s "$work/qtbase/lib/cmake/Qt6Core/Qt6CoreConfig.cmake" ] || { echo "Missing Qtbase prerequisites" >&2; exit 2; }
fi
if [ "$QT_HOST_RESUME_FROM" = qttools ]; then
    for tool in libexec/moc libexec/rcc libexec/uic bin/qsb; do
        [ -x "$work/qtbase/$tool" ] || { echo "Missing previous Qt host tool: $tool" >&2; exit 2; }
    done
    for module in Core CoreTools Svg ShaderTools Qml; do
        [ -s "$work/qtbase/lib/cmake/Qt6$module/Qt6${module}Config.cmake" ] || { echo "Missing previous Qt CMake package: $module" >&2; exit 2; }
    done
fi
if [ -d "$work/source/qtbase-everywhere-src-6.12.0" ] &&
    { [ -z "$QT_HOST_RESUME_FROM" ] || [ "$QT_HOST_RESUME_FROM" = qtbase-network ]; }; then
    if [ ! -f "$work/qtbase-network-source.sha256" ] && [ "$HOST_INCREMENTAL_RECONFIGURE" != 1 ]; then
        echo "Qtbase network owner patches require explicit incremental reconfigure" >&2; exit 2
    fi
    qtbase_action=apply
    [ "$plan_only" != 1 ] || qtbase_action=plan
    "$HOST_PYTHON" -I "$quick3d_transition" "$qtbase_action" \
        "$work/source/qtbase-everywhere-src-6.12.0" \
        "$distfiles/qtbase-everywhere-src-6.12.0.tar.xz" \
        "$work/qtbase-network-source.sha256" "$PATCH" $qtbase_network_patches
fi
if [ "$profile" = full ] && [ -d "$work/source/qttools-everywhere-src-6.12.0" ] &&
    { [ -z "$QT_HOST_RESUME_FROM" ] || [ "$QT_HOST_RESUME_FROM" = qttools ]; }; then
    if [ ! -f "$work/qttools-source.sha256" ] && [ "$HOST_INCREMENTAL_RECONFIGURE" != 1 ]; then
        echo "QtTools owner patch requires explicit incremental reconfigure" >&2; exit 2
    fi
    qttools_action=apply
    [ "$plan_only" != 1 ] || qttools_action=plan
    "$HOST_PYTHON" -I "$quick3d_transition" "$qttools_action" \
        "$work/source/qttools-everywhere-src-6.12.0" \
        "$distfiles/qttools-everywhere-src-6.12.0.tar.xz" \
        "$work/qttools-source.sha256" "$PATCH" "$qttools_patch"
fi
if [ "$profile" = full ] && [ -d "$work/source/qtquick3d-everywhere-src-6.12.0" ] &&
    { [ -z "$QT_HOST_RESUME_FROM" ] || [ "$QT_HOST_RESUME_FROM" = qtquick3d ]; }; then
    if [ ! -f "$work/qtquick3d-source.sha256" ] && [ "$HOST_INCREMENTAL_RECONFIGURE" != 1 ]; then
        echo 'Quick3D owner patches require explicit incremental reconfigure' >&2; exit 2
    fi
    quick3d_action=apply
    [ "$plan_only" != 1 ] || quick3d_action=plan
    "$HOST_PYTHON" -I "$quick3d_transition" "$quick3d_action" \
        "$work/source/qtquick3d-everywhere-src-6.12.0" \
        "$distfiles/qtquick3d-everywhere-src-6.12.0.tar.xz" \
        "$work/qtquick3d-source.sha256" "$PATCH" $quick3d_patches
fi
if [ "$plan_only" = 1 ]; then
    modules_csv=$(printf '%s' "$modules" | tr ' ' ',')
    printf 'PLAN: profile=%s modules=%s\n' "$profile" "$modules_csv"
    exit 0
fi
mkdir -p "$work"
mkdir -p "$work/source" "$work/bin"
ln -sf "$CMAKE" "$work/bin/cmake"
ln -sf "$NINJA" "$work/bin/ninja"
[ -z "$host_codesign" ] || ln -sf "$host_codesign" "$work/bin/codesign"
PATH="$work/bin:$PATH"
export PATH
{
    shasum -a 256 "$toolkit/cross/build-host-tools.sh" "$toolkit/cross/host-resume-inputs.py" $resume_otool_input "$toolkit/sources.tsv" "$HOST_SH" "$CMAKE" "$NINJA" "$TAR" "$PATCH" "$HOST_PYTHON" "$WAYLAND_SCANNER" "$HOST_CC" "$HOST_CXX" "$HOST_PKG_CONFIG" "$scanner_patch" "$syncqt_patch" "$zlib_patch" "$widgets_patch" "$markdown_patch" $shader_patches "$qttools_patch" $qtbase_network_patches $quick3d_inputs $host_dbus_inputs $runtime_inputs $host_codesign
    "$CMAKE" --version
    "$NINJA" --version
    printf 'profile=%s\n' "$profile"
    printf 'resume_from=%s\n' "$QT_HOST_RESUME_FROM"
    printf 'quick3d_build_dir=%s\n' "$HOST_QT_QUICK3D_BUILD_DIR"
    printf 'host_package_prefix=%s\n' "$HOST_PACKAGE_PREFIX"
    printf 'host_runtime_view=%s\n' "$HOST_RUNTIME_VIEW"
    printf 'host_runtime_view_identity=%s\n' "$runtime_view_identity"
    printf 'host_deployment_target=%s\n' "$host_deployment_target"
    printf 'host_darwin_sdk=%s\n' "$host_darwin_sdk"
    if [ "$profile" = full ]; then
        shasum -a 256 "$HOST_LLVM_BUILD/lib/cmake/llvm/LLVMConfig.cmake" \
            "$HOST_CLANG_BUILD/lib/cmake/clang/ClangConfig.cmake" \
            "$host_clang_library"
    fi
    "$HOST_CC" --version
} >> "$work/inputs.txt"
for module in $modules; do
    archive=$module-everywhere-src-6.12.0.tar.xz
    module_work=$work/$module
    [ "$module" != qtquick3d ] || module_work=$HOST_QT_QUICK3D_BUILD_DIR
    shasum -a 256 "$distfiles/$archive" >> "$work/inputs.txt"
    if [ -n "$QT_HOST_RESUME_FROM" ] && [ "$module" != "$QT_HOST_RESUME_FROM" ] &&
        ! { { [ "$QT_HOST_RESUME_FROM" = qtbase-network ] || [ "$QT_HOST_RESUME_FROM" = qtbase-xml ]; } && [ "$module" = qtbase ]; }; then
        continue
    fi
    if [ ! -d "$work/source/$module-everywhere-src-6.12.0" ]; then
        "$TAR" -xf "$distfiles/$archive" -C "$work/source"
        if [ "$module" = qtbase ]; then
            "$PATCH" -d "$work/source/$module-everywhere-src-6.12.0" -p0 -F0 -i "$scanner_patch"
            "$PATCH" -d "$work/source/$module-everywhere-src-6.12.0" -p0 -F0 -i "$syncqt_patch"
            "$PATCH" -d "$work/source/$module-everywhere-src-6.12.0" -p0 -F0 -i "$zlib_patch"
            "$PATCH" -d "$work/source/$module-everywhere-src-6.12.0" -p0 -F0 -i "$widgets_patch"
            "$PATCH" -d "$work/source/$module-everywhere-src-6.12.0" -p0 -F0 -i "$markdown_patch"
            "$HOST_PYTHON" -I "$quick3d_transition" apply \
                "$work/source/$module-everywhere-src-6.12.0" "$distfiles/$archive" \
                "$work/qtbase-network-source.sha256" "$PATCH" $qtbase_network_patches
            (cd "$work/source/$module-everywhere-src-6.12.0" &&
                shasum -a 256 src/tools/qtwaylandscanner/qtwaylandscanner.cpp src/tools/syncqt/CMakeLists.txt cmake/FindWrapSystemZLIB.cmake src/widgets/CMakeLists.txt src/gui/text/qtextmarkdownimporter.cpp > "$work/qtbase-scanner-source.sha256")
        elif [ "$module" = qtshadertools ]; then
            for patch in $shader_patches; do
                "$PATCH" -d "$work/source/$module-everywhere-src-6.12.0" -p0 -F0 -i "$patch"
            done
            (cd "$work/source/$module-everywhere-src-6.12.0" &&
                shasum -a 256 src/CMakeLists.txt src/shadertools/CMakeLists.txt src/shadertools/qspirvcompiler.cpp src/shadertools/qspirvshaderremap.cpp src/shadertools/qspirvshaderremap_p.h > "$work/qtshadertools-source.sha256")
        elif [ "$module" = qttools ]; then
            "$HOST_PYTHON" -I "$quick3d_transition" apply \
                "$work/source/$module-everywhere-src-6.12.0" "$distfiles/$archive" \
                "$work/qttools-source.sha256" "$PATCH" "$qttools_patch"
        elif [ "$module" = qtquick3d ]; then
            "$HOST_PYTHON" -I "$quick3d_transition" apply \
                "$work/source/$module-everywhere-src-6.12.0" "$distfiles/$archive" \
                "$work/qtquick3d-source.sha256" "$PATCH" $quick3d_patches
        fi
    fi
    mkdir -p "$module_work"
    for log in configure build; do
        if [ -f "$module_work/$log.log" ]; then
            mv "$module_work/$log.log" "$module_work/$log.before-resume-$$.log"
        fi
    done
    if [ "$module" = qtbase ]; then
        [ -f "$work/qtbase-scanner-source.sha256" ] &&
            (cd "$work/source/$module-everywhere-src-6.12.0" &&
                shasum -a 256 -c "$work/qtbase-scanner-source.sha256") || {
            echo 'Patched Qt scanner source proof failed; use a new work directory.' >&2; exit 2;
        }
        if [ "$QT_HOST_RESUME_FROM" = qtbase-xml ]; then
            "$CMAKE" --build "$module_work" --parallel "$JOBS" --target Xml > "$module_work/build.log" 2>&1
            continue
        fi
        # Find the portable XML generator on macOS too. Do this at initial
        # configure: developer builds cache failed package searches.
        set --
        [ -z "$host_deployment_target" ] || set -- "-DCMAKE_OSX_DEPLOYMENT_TARGET:STRING=$host_deployment_target"
        if [ -n "$host_darwin_sdk" ]; then
            set -- "$@" "-DCMAKE_OSX_SYSROOT:PATH=$host_darwin_sdk" \
                "-DCMAKE_FRAMEWORK_PATH:PATH=$host_darwin_sdk/System/Library/Frameworks" \
                "-DCUPS_INCLUDE_DIR:PATH=$host_darwin_sdk/usr/include" \
                "-DCUPS_LIBRARIES:FILEPATH=$host_darwin_sdk/usr/lib/libcups.tbd"
        fi
        [ -z "$HOST_RUNTIME_VIEW" ] || set -- "$@" "-DCMAKE_PROJECT_TOP_LEVEL_INCLUDES:FILEPATH=$runtime_cmake"
        (cd "$module_work" && CC="$HOST_CC" CXX="$HOST_CXX" \
            PKG_CONFIG="$HOST_PKG_CONFIG" PKG_CONFIG_LIBDIR="$HOST_PACKAGE_PREFIX/lib/pkgconfig:$HOST_PACKAGE_PREFIX/share/pkgconfig" PKG_CONFIG_PATH= \
            "$HOST_SH" "$work/source/$module-everywhere-src-6.12.0/configure" \
            -developer-build -opensource -confirm-license -release \
            -nomake tests -nomake examples -- \
            -DCMAKE_MAKE_PROGRAM="$NINJA" -DPython3_EXECUTABLE:FILEPATH="$HOST_PYTHON" -DQT_FIND_ALL_PACKAGES_ALWAYS=ON \
            -DCMAKE_PREFIX_PATH:PATH="$HOST_PACKAGE_PREFIX" -DZLIB_ROOT:PATH="$HOST_PACKAGE_PREFIX" -DPKG_CONFIG_EXECUTABLE:FILEPATH="$HOST_PKG_CONFIG" -DPKG_CONFIG_ARGN=--define-prefix \
            -DCMAKE_FIND_USE_CMAKE_SYSTEM_PATH:BOOL=OFF -DCMAKE_FIND_USE_CMAKE_ENVIRONMENT_PATH:BOOL=OFF \
            -DCMAKE_FIND_USE_PACKAGE_REGISTRY:BOOL=OFF -DCMAKE_FIND_USE_SYSTEM_PACKAGE_REGISTRY:BOOL=OFF \
            -DCMAKE_IGNORE_PATH:STRING=/usr/X11/include \
            -Uzstd_DIR -UZSTD'*' -UFontconfig'*' -UPostgreSQL'*' -UFIND_PACKAGE_MESSAGE_DETAILS_PostgreSQL \
            -DFEATURE_system_doubleconversion=ON -DFEATURE_system_freetype=ON -DFEATURE_system_harfbuzz=ON \
            -DFEATURE_system_jpeg=ON -DFEATURE_system_libb2=ON -DFEATURE_system_pcre2=ON \
            -DFEATURE_system_png=ON -DFEATURE_system_sqlite=ON -DFEATURE_system_textmarkdownreader=ON -DFEATURE_system_zlib=ON \
            -UQT_INTERNAL_PREVIOUSLY_FOUND_PACKAGES \
            -UQT_INTERNAL_PREVIOUSLY_SEARCHED_PACKAGES \
            -DDBus1_DIR="$HOST_DBUS_PREFIX/lib/cmake/DBus1" \
            -DDBus1_LIBRARY:FILEPATH="$host_dbus_library" \
            -DDBus1_INCLUDE_DIR:PATH="$HOST_DBUS_PREFIX/include/dbus-1.0" \
            -DDBus1_ARCH_INCLUDE_DIR:PATH="$HOST_DBUS_PREFIX/lib/dbus-1.0/include" \
            -DFEATURE_dbus=ON -DFEATURE_dbus_linked=ON -DFEATURE_publicsuffix_libpsl=ON -DFEATURE_publicsuffix_qt=OFF -DFEATURE_publicsuffix_system=OFF -DFEATURE_pkg_config=ON \
            -DWaylandScanner_EXECUTABLE="$WAYLAND_SCANNER" \
            -DFEATURE_qtwaylandscanner=ON "$@") > "$module_work/configure.log" 2>&1
        # Qt can reset a requested feature when a dependency search was cached.
        # Reject that result before an XML generator can emit empty signatures.
        grep -q -x 'FEATURE_dbus_linked:BOOL=ON' "$module_work/CMakeCache.txt"
        grep -q -x 'QT_FEATURE_dbus_linked:INTERNAL=ON' "$module_work/CMakeCache.txt"
        grep -F -x "ZLIB_ROOT:PATH=$HOST_PACKAGE_PREFIX" "$module_work/CMakeCache.txt" >/dev/null || {
            echo 'Qt did not retain the selected zlib root' >&2; exit 1;
        }
        for feature in doubleconversion freetype harfbuzz jpeg libb2 pcre2 png sqlite textmarkdownreader zlib; do
            grep -F -x "QT_FEATURE_system_${feature}:INTERNAL=ON" "$module_work/CMakeCache.txt" >/dev/null || {
                echo "Qt system dependency was not selected: $feature" >&2; exit 1;
            }
        done
        for variable in FREETYPE_LIBRARY_RELEASE HARFBUZZ_LIBRARIES JPEG_LIBRARY_RELEASE LIBB2_LIBRARY PCRE2_LIBRARY_RELEASE PNG_LIBRARY_RELEASE SQLite3_LIBRARY ZLIB_LIBRARY_RELEASE double-conversion_DIR md4c_DIR; do
            value=$(sed -n -e "s/^${variable}:FILEPATH=//p" -e "s/^${variable}:PATH=//p" "$module_work/CMakeCache.txt")
            case "$value" in "$HOST_PACKAGE_PREFIX"/*) ;; *)
                echo "Qt dependency is outside selected native prefix: $variable" >&2; exit 1;; esac
        done
        if grep -E "/opt/homebrew/|/usr/local/" "$module_work/build.ninja" >/dev/null; then
            echo "Unselected external dependency in Qt build graph" >&2; exit 1
        fi
        grep -F -x "QT_FEATURE_publicsuffix_libpsl:INTERNAL=ON" "$module_work/CMakeCache.txt" >/dev/null || { echo "Qt did not select common libpsl" >&2; exit 1; }
        for feature in qt system; do
            grep -F -x "QT_FEATURE_publicsuffix_${feature}:INTERNAL=OFF" "$module_work/CMakeCache.txt" >/dev/null || { echo "Conflicting Qt public suffix backend: $feature" >&2; exit 1; }
        done
        if [ "$QT_HOST_RESUME_FROM" = qtbase-network ]; then
            "$CMAKE" --build "$module_work" --parallel "$JOBS" --target Network host_tools > "$module_work/build.log" 2>&1
            continue
        fi
        # Other modules' host generators link these libraries. Their metadata
        # alone is insufficient when the modules are built independently.
        "$CMAKE" --build "$module_work" --parallel "$JOBS" \
            --target host_tools Gui Network Widgets OpenGL Sql Concurrent Test PrintSupport QSQLiteDriverPlugin QMinimalIntegrationPlugin \
            > "$module_work/build.log" 2>&1
    else
        set --
        [ "$module" != qtdeclarative ] || set -- -DFEATURE_quick_vectorimage=ON
        [ "$module" != qtquick3d ] || set -- "$@" -DINPUT_quick3d_assimp:STRING=system -DFEATURE_system_assimp:BOOL=ON
        if [ "$module" = qtquick3d ] && [ "$HOST_INCREMENTAL_RECONFIGURE" = 1 ]; then
            # A previous configure may have cached the old provider search failure.
            set -- "$@" -U HAVE_quick3d_assimp -U TEST_quick3d_assimp
        fi
        if [ "$module" = qtshadertools ]; then
            set -- "$@" "-DSPIRV-Tools_DIR:PATH=$HOST_PACKAGE_PREFIX/lib/cmake/SPIRV-Tools" \
                "-DSPIRV-Tools-opt_DIR:PATH=$HOST_PACKAGE_PREFIX/lib/cmake/SPIRV-Tools-opt"
        fi
        set -- "$@" "-DCMAKE_PREFIX_PATH:PATH=$HOST_PACKAGE_PREFIX"
        set -- "$@" "-DZLIB_ROOT:PATH=$HOST_PACKAGE_PREFIX"
        [ -z "$HOST_RUNTIME_VIEW" ] || set -- "$@" "-DCMAKE_PROJECT_TOP_LEVEL_INCLUDES:FILEPATH=$runtime_cmake"
        if [ "$module" = qttools ]; then
            set -- "$@" -DLLVM_DIR="$HOST_LLVM_BUILD/lib/cmake/llvm" \
                -DClang_DIR="$HOST_CLANG_BUILD/lib/cmake/clang" \
                -DFEATURE_clang=ON -DFEATURE_qdoc=ON
            # Upstream macOS archives contain LLVM 23 LTO bitcode. Apple ld's
            # bundled older reader cannot decode it; select the matching plugin.
            if [ "$(uname -s)" = Darwin ] && [ -s "$HOST_LLVM_BUILD/lib/libLTO.dylib" ]; then
                set -- "$@" "-DCMAKE_EXE_LINKER_FLAGS=-Wl,-lto_library,$HOST_LLVM_BUILD/lib/libLTO.dylib"
                shasum -a 256 "$HOST_LLVM_BUILD/lib/libLTO.dylib" >> "$work/inputs.txt"
            fi
        fi
        # Qt runs project-signature try_compile in a separate CMake process.
        # Its package search must retain the selected native prefix as well.
        (cd "$module_work" && CMAKE_PREFIX_PATH="$HOST_PACKAGE_PREFIX" "$HOST_SH" "$work/qtbase/bin/qt-configure-module" \
            "$work/source/$module-everywhere-src-6.12.0" \
            -- -DQT_BUILD_TESTS=OFF -DQT_BUILD_EXAMPLES=OFF -DPython3_EXECUTABLE:FILEPATH="$HOST_PYTHON" "$@") > "$module_work/configure.log" 2>&1
        grep -F -x "ZLIB_ROOT:PATH=$HOST_PACKAGE_PREFIX" "$module_work/CMakeCache.txt" >/dev/null || {
            echo 'Qt module did not retain the selected zlib root' >&2; exit 1;
        }
        if [ "$module" = qtshadertools ]; then
            for provider in SPIRV-Tools SPIRV-Tools-opt; do
                grep -F -x "${provider}_DIR:PATH=$HOST_PACKAGE_PREFIX/lib/cmake/$provider" "$module_work/CMakeCache.txt" >/dev/null || {
                    echo "Qt ShaderTools dependency is outside selected native prefix: $provider" >&2; exit 1;
                }
            done
        fi
        if [ "$module" = qtquick3d ]; then
            grep -F -x "QT_FEATURE_system_assimp:INTERNAL=ON" "$module_work/CMakeCache.txt" >/dev/null || {
                echo 'QtQuick3D did not select system Assimp' >&2; exit 1;
            }
        fi
        target=host_tools
        [ "$module" != qtsvg ] || target=Svg
        [ "$module" != qtquicktimeline ] || target=QuickTimeline
        set -- "$target"
        # balsam's executable alone cannot import assets without this plugin.
        [ "$module" != qtquick3d ] || set -- host_tools AssimpImporterPlugin
        "$CMAKE" --build "$module_work" --parallel "$JOBS" --target "$@" \
            > "$module_work/build.log" 2>&1
    fi
done
if [ -n "$HOST_RUNTIME_VIEW" ]; then
    qt_version=$("$HOST_PYTHON" -I "$runtime_launcher" --runtime-view "$HOST_RUNTIME_VIEW" -- "$work/qtbase/bin/qmake" -query QT_VERSION)
else
    qt_version=$("$work/qtbase/bin/qmake" -query QT_VERSION)
fi
[ "$qt_version" = 6.12.0 ]
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

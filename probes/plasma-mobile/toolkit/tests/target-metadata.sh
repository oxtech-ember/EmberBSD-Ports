#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted installed Qt metadata regression.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 QTBASE_RECIPE NEW_WORK" >&2; exit 2; }
recipe=$(CDPATH= cd -- "$1" && pwd)
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
root="$work/staged qt"
sysroot="$work/target root"
build="$work/build directory"
mkdir -p "$root/bin" "$root/libexec" "$root/lib/cmake/Qt6" "$root/mkspecs/preliminary" "$root/mkspecs/netbsd-g++"
printf 'target executable placeholder\n' > "$root/bin/qmake"
printf 'unchanged Qt config\n' > "$root/lib/cmake/Qt6/Qt6Config.cmake"
for wrapper in host-qmake host-qmake6 host-qtpaths host-qtpaths6 target_qt.conf; do
    printf 'host-only wrapper\n' > "$root/bin/$wrapper"
done
printf 'intermediate\n' > "$root/mkspecs/preliminary/transient.conf"
cat > "$root/mkspecs/qmodule.pri" <<EOF
CONFIG += shared cross_compile c++17
QT.global_private.enabled_features = cross_compile dbus
QT.global_private.disabled_features = static
PKG_CONFIG_EXECUTABLE = $build/tools/pkg-config
QMAKE_INCDIR = $sysroot/usr/pkg/include
QMAKE_LIBDIR = $build/.buildlink/lib
EOF
cat > "$root/mkspecs/netbsd-g++/qmake.conf" <<EOF
QMAKE_CC = $build/cc
QMAKE_CXX = $build/c++
EOF
cat > "$root/lib/cmake/Qt6/Qt6Dependencies.cmake" <<EOF
set(__qt_platform_initial_qt_host_path "/private/host-qt")
set(__qt_platform_initial_qt_host_path_cmake_dir "/private/host-qt/lib/cmake")
set(QT_SOURCE_TREE "$build/source" CACHE PATH "")
EOF
cat > "$root/lib/cmake/Qt6/Qt6Targets.cmake" <<'EOF'
get_filename_component(_IMPORT_PREFIX "${CMAKE_CURRENT_LIST_FILE}" PATH)
INTERFACE_INCLUDE_DIRECTORIES "/usr/pkg/include"
INTERFACE_LINK_DIRECTORIES "/usr/pkg/lib"
EOF
for file in bin/qt-cmake bin/qt-cmake-create libexec/qt-cmake-private; do
    printf '#!/bin/sh\noriginal_cmake_path="/private/host/cmake"\n' > "$root/$file"
    chmod 755 "$root/$file"
done
perl "$recipe/files/target-metadata.pl" "$root" "$sysroot" "$build" /usr/pkg
[ ! -e "$root/bin/host-qmake" ] && [ ! -e "$root/mkspecs/preliminary" ]
grep -qx 'QMAKE_CC = /usr/pkg/gcc16/bin/gcc' "$root/mkspecs/netbsd-g++/qmake.conf"
grep -qx 'QMAKE_CXX = /usr/pkg/gcc16/bin/g++' "$root/mkspecs/netbsd-g++/qmake.conf"
grep -qx 'QMAKE_INCDIR = /usr/pkg/include' "$root/mkspecs/qmodule.pri"
grep -qx 'QMAKE_LIBDIR = /usr/pkg/lib' "$root/mkspecs/qmodule.pri"
grep -qx 'QT.global_private.disabled_features = static cross_compile' "$root/mkspecs/qmodule.pri"
grep -qx 'HostSpec=netbsd-g++' "$root/bin/qt.conf"
grep -qx 'set(__qt_platform_initial_qt_host_path "")' "$root/lib/cmake/Qt6/Qt6Dependencies.cmake"
grep -Fqx 'INTERFACE_INCLUDE_DIRECTORIES "${_IMPORT_PREFIX}/../include"' "$root/lib/cmake/Qt6/Qt6Targets.cmake"
[ -x "$root/bin/qt-cmake" ]
find "$root" -type f -exec cksum {} \; | sort > "$work/first"
perl "$recipe/files/target-metadata.pl" "$root" "$sysroot" "$build" /usr/pkg
find "$root" -type f -exec cksum {} \; | sort > "$work/second"
cmp "$work/first" "$work/second"
printf 'unexpected = %s/unhandled\n' "$build" > "$root/mkspecs/invalid.pri"
if perl "$recipe/files/target-metadata.pl" "$root" "$sysroot" "$build" /usr/pkg > "$work/reject.log" 2>&1; then
    echo 'unresolved build path was accepted' >&2; exit 1
fi
grep -q 'unresolved build path' "$work/reject.log"
module="$work/staged module"
mkdir -p "$module/lib/cmake/Qt6Svg"
printf 'QMAKE_PRL_LIBS = -L"%s/usr/pkg/lib" -lGL\n' "$sysroot" > "$module/lib/libQt6Svg.prl"
perl "$recipe/files/target-metadata.pl" "$module" "$sysroot" "$build" /usr/pkg --module
grep -qx 'QMAKE_PRL_LIBS = -L"/usr/pkg/lib" -lGL' "$module/lib/libQt6Svg.prl"
[ ! -e "$module/bin/qt.conf" ]
echo 'PASS: target paths, generators, permissions, repeat install and host-path rejection'

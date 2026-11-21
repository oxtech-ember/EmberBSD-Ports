#!/bin/sh
# SPDX-License-Identifier: BSD-3-Clause
# Configure only the original Workspace menu data, without enabling compilers.
set -eu
umask 077
: "${WORKSPACE_ROOT:=$HOME/.cache/emberbsd-plasma-workspace}"
WORKSPACE_ROOT=$(CDPATH= cd -- "$WORKSPACE_ROOT" && pwd)
cache="$WORKSPACE_ROOT/build/CMakeCache.txt"
export PATH=/usr/pkg/bin:/usr/bin:/bin

cache_value()
{
    awk -v key="$1" '
        index($0, key ":") == 1 { sub(/^[^=]*=/, ""); print; found++ }
        END { if (found != 1) exit 1 }
    ' "$cache"
}

source_dir=$(cache_value CMAKE_HOME_DIRECTORY)
prefix=$(cache_value CMAKE_INSTALL_PREFIX)
desktop_dir=$(cache_value KDE_INSTALL_DESKTOPDIR)
dataroot_dir=$(cache_value KDE_INSTALL_DATAROOTDIR)
sysconf_dir=$(cache_value KDE_INSTALL_SYSCONFDIR)
# Empty ECM cache entries retain these upstream KDEInstallDirsCommon defaults.
: "${dataroot_dir:=share}"
: "${desktop_dir:=$dataroot_dir/desktop-directories}"
if grep -E '^(SHARE_INSTALL_PREFIX|XDG_DIRECTORY_INSTALL_DIR|CMAKE_INSTALL_DATAROOTDIR):[^=]*=.' "$cache"; then
    echo 'Unsupported legacy menu directory override' >&2
    exit 1
fi
if [ "$source_dir" != "$WORKSPACE_ROOT/src/plasma-workspace-6.8.3" ] ||
   [ "$prefix" != "$WORKSPACE_ROOT/prefix" ] ||
   [ "$dataroot_dir" != share ] || [ "$desktop_dir" != share/desktop-directories ] || [ "$sysconf_dir" != etc ]; then
    echo 'Unexpected Workspace source, private prefix, or relative menu install directories' >&2
    exit 1
fi
test -f "$source_dir/menu/desktop/plasma-applications.menu"
data_root=$(mktemp -d "$WORKSPACE_ROOT/menu-data.XXXXXX")
mkdir "$data_root/source"
cat > "$data_root/source/CMakeLists.txt" <<'CMAKE'
cmake_minimum_required(VERSION 3.16)
project(WorkspaceMenuData LANGUAGES NONE)
add_subdirectory("${WORKSPACE_SOURCE_DIR}/menu" menu)
CMAKE
cmake -S "$data_root/source" -B "$data_root/build" -G Ninja \
    -DWORKSPACE_SOURCE_DIR="$source_dir" -DCMAKE_INSTALL_PREFIX="$prefix" \
    -DKDE_INSTALL_DESKTOPDIR="$desktop_dir" -DKDE_INSTALL_SYSCONFDIR="$sysconf_dir"
if grep -E '^CMAKE_(C|CXX)_COMPILER:' "$data_root/build/CMakeCache.txt"; then
    echo 'Unexpected compiler configuration in data-only project' >&2
    exit 1
fi
printf 'Menu data build directory: %s\n' "$data_root/build"
printf 'Inspect %s/menu/desktop/cmake_install.cmake before cmake --install.\n' "$data_root/build"

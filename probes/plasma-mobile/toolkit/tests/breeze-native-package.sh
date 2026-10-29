#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). A cross Breeze Icons build gets its native
# generators from a Ports TOOL_DEPENDS package, never from a configured
# prefix, so a bulk fetch or parse needs no build-host setting.
set -eu
[ "$#" = 3 ] || { echo 'Usage: breeze-native-package.sh PKGSRC CROSS_MAKECONF NEW_WORK' >&2; exit 2; }
pkgsrc=$1 cross=$2 work=$3
: "${BMAKE:=bmake}"
mkdir "$work"
query() { # MAKECONF PKGPATH ARGS...
    config=$1 path=$2; shift 2
    MAKECONF="$config" "$BMAKE" -C "$pkgsrc/$path" _MAKEVARS_MK=defined _PKGSRC_BARRIER=yes "$@"
}
generators='breeze-icons-generators-6.31.0{,nb[0-9]*}:../../graphics/breeze-icons-generators'
query "$cross" graphics/breeze-icons -V '${USE_CROSS_COMPILE:tl}' -V '${PKG_FAIL_REASON}' \
    -V '${TOOL_DEPENDS}' -V '${CMAKE_CONFIGURE_ARGS}' -V '${TOOLBASE}' > "$work/target.txt"
[ "$(sed -n 1p "$work/target.txt")" = yes ]
if sed -n 2p "$work/target.txt" | grep -q .; then
    echo "graphics/breeze-icons cannot be fetched or built: $(sed -n 2p "$work/target.txt")" >&2; exit 1
fi
toolbase=$(sed -n 5p "$work/target.txt")
[ -n "$toolbase" ]
sed -n 3p "$work/target.txt" | tr -s ' ' '\n' | grep -Fqx "$generators" ||
    { echo 'graphics/breeze-icons does not depend on the native generators' >&2; exit 1; }
sed -n 4p "$work/target.txt" | tr -s ' ' '\n' > "$work/cmake.txt"
for arg in "-DKF6_HOST_TOOLING=$toolbase/bin" \
    "-DGENERATE_SYMBOLIC_DARK=$toolbase/bin/generate-symbolic-dark" \
    "-DQRC_ALIAS=$toolbase/bin/qrcAlias"; do
    grep -Fqx -- "$arg" "$work/cmake.txt" || { echo "Missing CMake argument: $arg" >&2; exit 1; }
done
if grep -q BREEZE_HOST "$work/target.txt"; then exit 1; fi
# The former prefix variable no longer selects anything.
query "$cross" graphics/breeze-icons EMBERBSD_KF6_BREEZE_HOST=/nonexistent-ember-generator \
    -V '${PKG_FAIL_REASON}' -V '${CMAKE_CONFIGURE_ARGS}' > "$work/legacy.txt"
if grep -q nonexistent-ember-generator "$work/legacy.txt"; then exit 1; fi
query "$cross" graphics/breeze-icons -n emberbsd-native-breeze-check > "$work/check-plan.txt"
grep -Fq "$toolbase/bin/generate-symbolic-dark" "$work/check-plan.txt"
grep -Fq "$toolbase/bin/qrcAlias" "$work/check-plan.txt"
# A TOOL_DEPENDS recursion builds the generators natively from the same
# release, and the package refuses cross builds.
query "$cross" graphics/breeze-icons-generators USE_CROSS_COMPILE=no -V '${USE_CROSS_COMPILE:Uno:tl}' \
    -V '${PKG_FAIL_REASON}' -V '${PKGNAME}' -V '${DISTFILES}' -V '${CMAKE_CONFIGURE_ARGS}' \
    -V '${DISTINFO_FILE}' -V '${PATCHDIR}' > "$work/native.txt"
[ "$(sed -n 1p "$work/native.txt")" = no ]
# The generators add no failure of their own to a native CMake build: compare
# with a native KF6 CMake package in the same configuration.
query "$cross" archivers/kf6-karchive USE_CROSS_COMPILE=no -V '${PKG_FAIL_REASON}' > "$work/native-reference.txt"
sed -n 2p "$work/native.txt" | cmp -s - "$work/native-reference.txt" ||
    { echo "The native generators cannot be built: $(sed -n 2p "$work/native.txt")" >&2; exit 1; }
[ "$(sed -n 3p "$work/native.txt")" = breeze-icons-generators-6.31.0 ]
[ "$(sed -n 4p "$work/native.txt")" = "$(query "$cross" graphics/breeze-icons -V '${DISTFILES}')" ]
for arg in -DINSTALL_HOST_TOOLS=ON -DSKIP_INSTALL_ICONS=ON -DWITH_ICONS_LIBRARY=OFF; do
    sed -n 5p "$work/native.txt" | tr -s ' ' '\n' | grep -Fqx -- "$arg"
done
[ "$(sed -n 6p "$work/native.txt")" = "$(query "$cross" graphics/breeze-icons -V '${DISTINFO_FILE}')" ]
[ "$(sed -n 7p "$work/native.txt")" = "$(query "$cross" graphics/breeze-icons -V '${PATCHDIR}')" ]
query "$cross" graphics/breeze-icons-generators -V '${PKG_FAIL_REASON}' > "$work/cross-generators.txt"
grep -q 'build-host tool' "$work/cross-generators.txt"
echo 'PASS: Breeze Icons cross builds use the native Ports generators and need no host setting'

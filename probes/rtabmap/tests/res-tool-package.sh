#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). A cross RTAB-Map build gets its native
# resource generator from a Ports TOOL_DEPENDS package, never from a
# configured path, so a bulk fetch or parse needs no build-host setting.
set -eu
[ "$#" = 3 ] || { echo 'Usage: res-tool-package.sh PKGSRC CROSS_MAKECONF NEW_WORK' >&2; exit 2; }
pkgsrc=$1 cross=$2 work=$3
: "${BMAKE:=bmake}"
mkdir "$work"
query() { # PKGPATH ARGS...
    path=$1; shift
    MAKECONF="$cross" "$BMAKE" -C "$pkgsrc/$path" _MAKEVARS_MK=defined _PKGSRC_BARRIER=yes "$@"
}
tool='rtabmap-res-tool-0.23.8{,nb[0-9]*}:../../local-robotics/rtabmap-res-tool'
query local-robotics/rtabmap -V '${USE_CROSS_COMPILE:tl}' -V '${PKG_FAIL_REASON}' \
    -V '${TOOL_DEPENDS}' -V '${CMAKE_CONFIGURE_ARGS}' -V '${TOOLBASE}' > "$work/target.txt"
[ "$(sed -n 1p "$work/target.txt")" = yes ]
if sed -n 2p "$work/target.txt" | grep -q .; then
    echo "local-robotics/rtabmap cannot be fetched or built: $(sed -n 2p "$work/target.txt")" >&2; exit 1
fi
toolbase=$(sed -n 5p "$work/target.txt")
[ -n "$toolbase" ]
sed -n 3p "$work/target.txt" | tr -s ' ' '\n' | grep -Fqx "$tool" ||
    { echo 'local-robotics/rtabmap does not depend on the native resource tool' >&2; exit 1; }
sed -n 4p "$work/target.txt" | tr -s ' ' '\n' | grep -Fqx -- "-DRTABMAP_RES_TOOL=$toolbase/bin/rtabmap-res_tool" ||
    { echo 'RTABMAP_RES_TOOL does not name the TOOLBASE tool' >&2; exit 1; }
# The former path variable no longer selects anything.
query local-robotics/rtabmap RTABMAP_NATIVE_RES_TOOL=/nonexistent-ember-res-tool \
    -V '${PKG_FAIL_REASON}' -V '${CMAKE_CONFIGURE_ARGS}' > "$work/legacy.txt"
if grep -q nonexistent-ember-res-tool "$work/legacy.txt"; then exit 1; fi
query local-robotics/rtabmap -n emberbsd-native-rtabmap-res-tool-check > "$work/check-plan.txt"
grep -Fq "$toolbase/bin/rtabmap-res_tool" "$work/check-plan.txt"
# The TOOL_DEPENDS recursion builds the tool natively from the same source,
# distinfo and patches; it adds no failure of its own to a native build.
query local-robotics/rtabmap-res-tool USE_CROSS_COMPILE=no -V '${USE_CROSS_COMPILE:Uno:tl}' \
    -V '${PKG_FAIL_REASON}' -V '${PKGNAME}' -V '${DISTFILES}' -V '${CMAKE_CONFIGURE_ARGS}' \
    -V '${DISTINFO_FILE}' -V '${PATCHDIR}' -V '${BUILD_TARGET}' > "$work/native.txt"
query local-robotics/rtabmap USE_CROSS_COMPILE=no -V '${PKG_FAIL_REASON}' -V '${DISTFILES}' \
    -V '${DISTINFO_FILE}' -V '${PATCHDIR}' > "$work/native-library.txt"
[ "$(sed -n 1p "$work/native.txt")" = no ]
[ "$(sed -n 2p "$work/native.txt")" = "$(sed -n 1p "$work/native-library.txt")" ] ||
    { echo "The native resource tool cannot be built: $(sed -n 2p "$work/native.txt")" >&2; exit 1; }
[ "$(sed -n 3p "$work/native.txt")" = rtabmap-res-tool-0.23.8 ]
[ "$(sed -n 4p "$work/native.txt")" = "$(sed -n 2p "$work/native-library.txt")" ]
sed -n 5p "$work/native.txt" | tr -s ' ' '\n' | grep -Fqx -- -DANDROID_PREBUILD=ON
[ "$(sed -n 6p "$work/native.txt")" = "$(sed -n 3p "$work/native-library.txt")" ]
[ "$(sed -n 7p "$work/native.txt")" = "$(sed -n 4p "$work/native-library.txt")" ]
[ "$(sed -n 8p "$work/native.txt")" = res_tool ]
query local-robotics/rtabmap-res-tool -V '${PKG_FAIL_REASON}' > "$work/cross-tool.txt"
grep -q 'build-host tool' "$work/cross-tool.txt"
echo 'PASS: RTAB-Map cross builds use the native Ports resource tool and need no host setting'

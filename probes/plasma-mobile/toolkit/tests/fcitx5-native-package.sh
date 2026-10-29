#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). A cross Fcitx5 build gets its native
# spell dictionary compiler from a Ports TOOL_DEPENDS package, never from a
# configured path, so a bulk fetch or parse needs no build-host setting.
set -eu
[ "$#" = 3 ] || { echo 'Usage: fcitx5-native-package.sh PKGSRC CROSS_MAKECONF NEW_WORK' >&2; exit 2; }
pkgsrc=$1 cross=$2 work=$3
: "${BMAKE:=bmake}"
mkdir "$work"
query() { # PKGPATH ARGS...
    path=$1; shift
    MAKECONF="$cross" "$BMAKE" -C "$pkgsrc/$path" _MAKEVARS_MK=defined _PKGSRC_BARRIER=yes "$@"
}
tool='fcitx5-comp-spell-dict-5.1.23{,nb[0-9]*}:../../inputmethod/fcitx5-comp-spell-dict'
query inputmethod/fcitx5 -V '${USE_CROSS_COMPILE:tl}' -V '${PKG_FAIL_REASON}' \
    -V '${TOOL_DEPENDS}' -V '${CMAKE_CONFIGURE_ARGS}' -V '${TOOLBASE}' > "$work/target.txt"
[ "$(sed -n 1p "$work/target.txt")" = yes ]
if sed -n 2p "$work/target.txt" | grep -q .; then
    echo "inputmethod/fcitx5 cannot be fetched or built: $(sed -n 2p "$work/target.txt")" >&2; exit 1
fi
toolbase=$(sed -n 5p "$work/target.txt")
[ -n "$toolbase" ]
sed -n 3p "$work/target.txt" | tr -s ' ' '\n' | grep -Fqx "$tool" ||
    { echo 'inputmethod/fcitx5 does not depend on the native dictionary compiler' >&2; exit 1; }
sed -n 4p "$work/target.txt" | tr -s ' ' '\n' | grep -Fqx -- "-DFCITX5_HOST_COMP_SPELL_DICT:FILEPATH=$toolbase/bin/fcitx5-comp-spell-dict" ||
    { echo 'FCITX5_HOST_COMP_SPELL_DICT does not name the TOOLBASE tool' >&2; exit 1; }
# The former path variable no longer selects anything.
query inputmethod/fcitx5 EMBERBSD_FCITX5_COMP_SPELL_DICT=/nonexistent-ember-spell-dict \
    -V '${PKG_FAIL_REASON}' -V '${CMAKE_CONFIGURE_ARGS}' > "$work/legacy.txt"
if grep -q nonexistent-ember-spell-dict "$work/legacy.txt"; then exit 1; fi
# The TOOL_DEPENDS recursion builds the compiler natively from the same source,
# distinfo and patches; it adds no failure of its own to a native build.
query inputmethod/fcitx5-comp-spell-dict USE_CROSS_COMPILE=no -V '${USE_CROSS_COMPILE:Uno:tl}' \
    -V '${PKG_FAIL_REASON}' -V '${PKGNAME}' -V '${DISTFILES}' -V '${CMAKE_CONFIGURE_ARGS}' \
    -V '${DISTINFO_FILE}' -V '${PATCHDIR}' -V '${BUILD_TARGET}' > "$work/native.txt"
query inputmethod/fcitx5 USE_CROSS_COMPILE=no -V '${PKG_FAIL_REASON}' -V '${DISTFILES}' \
    -V '${DISTINFO_FILE}' -V '${PATCHDIR}' > "$work/native-library.txt"
[ "$(sed -n 1p "$work/native.txt")" = no ]
[ "$(sed -n 2p "$work/native.txt")" = "$(sed -n 1p "$work/native-library.txt")" ] ||
    { echo "The native dictionary compiler cannot be built: $(sed -n 2p "$work/native.txt")" >&2; exit 1; }
[ "$(sed -n 3p "$work/native.txt")" = fcitx5-comp-spell-dict-5.1.23 ]
[ "$(sed -n 4p "$work/native.txt")" = "$(sed -n 2p "$work/native-library.txt")" ]
sed -n 5p "$work/native.txt" | tr -s ' ' '\n' | grep -Fqx -- -DBUILD_SPELL_DICT=ON
[ "$(sed -n 6p "$work/native.txt")" = "$(sed -n 3p "$work/native-library.txt")" ]
[ "$(sed -n 7p "$work/native.txt")" = "$(sed -n 4p "$work/native-library.txt")" ]
[ "$(sed -n 8p "$work/native.txt")" = comp-spell-dict ]
query inputmethod/fcitx5-comp-spell-dict -V '${PKG_FAIL_REASON}' > "$work/cross-tool.txt"
grep -q 'build-host tool' "$work/cross-tool.txt"
echo 'PASS: Fcitx5 cross builds use the native Ports dictionary compiler and need no host setting'

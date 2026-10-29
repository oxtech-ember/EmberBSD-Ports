#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Native TOOL_DEPENDS recursion from a cross
# package must use the host prefix compiler, never pkgsrc GCC or plain cc.
set -eu
[ "$#" = 3 ] || { echo "Usage: $0 EXPORTED_PKGSRC CROSS_MAKECONF NEW_WORK" >&2; exit 2; }
pkgsrc=$1 makeconf=$2 work=$3
bmake=${BMAKE:-bmake}
for path in "$pkgsrc" "$makeconf" "$work"; do
    case "$path" in /*) ;; *) exit 2 ;; esac
    case "$path" in *[!a-zA-Z0-9_./-]*) exit 2 ;; esac
done
mkdir "$work"
# Recurse exactly as mk/pkgformat/pkg/depends.mk installs a native tool.
cat > "$work/recursion.mk" <<'MAKE'
.PHONY: ember-native
ember-native:
	@cd ../../devel/py-meson_python && unset MAKEFLAGS && \
	 ${PKGSRC_SETENV} ${PKGSRC_MAKE_ENV} USE_CROSS_COMPILE=no \
	 ${MAKE} ${_DEPENDS_MAKEFLAGS} show-vars \
	 VARNAMES='EMBERBSD_HOST_COMPILER_FAMILY PKGSRC_COMPILER _EMBER_SDK_CC PKG_CC CLANGBASE USE_PKGSRC_GCC BUILD_DEPENDS PKG_FAIL_REASON'
MAKE
"$bmake" -C "$pkgsrc/math/py-numpy" MAKECONF="$makeconf" -f Makefile -f "$work/recursion.mk" \
    ember-native > "$work/native.txt" 2> "$work/native.err"
line() { sed -n "$1p" "$work/native.txt"; }
family=$(line 1)
[ -n "$family" ] && [ "$(line 2)" = "$family" ] || {
    echo "FAIL: native recursion selects PKGSRC_COMPILER '$(line 2)', not '$family'" >&2; exit 1; }
[ -n "$(line 3)" ] && [ "$(line 4)" = "$(line 3)" ] || {
    echo "FAIL: native recursion uses CC '$(line 4)', not '$(line 3)'" >&2; exit 1; }
[ "$family" != clang ] || [ "$(line 4)" = "$(line 5)/bin/clang" ] || {
    echo 'FAIL: native Clang is outside CLANGBASE' >&2; exit 1; }
[ "$(line 6)" = no ] || { echo 'FAIL: native recursion selects pkgsrc GCC' >&2; exit 1; }
if line 7 | grep -q 'gcc16'; then
    echo "FAIL: native recursion depends on GCC16: $(line 7)" >&2; exit 1
fi
[ -z "$(line 8)" ] || { echo "FAIL: native recursion refuses: $(line 8)" >&2; exit 1; }
echo "PASS: native dependency recursion selects the host prefix $family compiler"
"$bmake" -C "$pkgsrc/math/blas" MAKECONF="$makeconf" -v EMBERBSD_CROSS_COMPILER_FAMILY \
    -v PKGSRC_COMPILER -v PKG_CC -v TOOLDIR > "$work/cross.txt" 2> "$work/cross.err"
cross_cc=$(sed -n 3p "$work/cross.txt") tooldir=$(sed -n 4p "$work/cross.txt")
[ "$(sed -n 2p "$work/cross.txt")" = "$(sed -n 1p "$work/cross.txt")" ] || {
    echo 'FAIL: cross package left the cross compiler family' >&2; exit 1; }
case "$cross_cc" in "$tooldir"/bin/*) ;; *)
    echo "FAIL: cross package CC '$cross_cc' left the cross tools" >&2; exit 1 ;; esac
echo 'PASS: cross packages keep the cross compiler'

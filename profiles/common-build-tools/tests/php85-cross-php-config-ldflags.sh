#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake php85-cross-php-config-ldflags.sh PKGSRC MAKECONF NEW_WORK
#
# php-config records in ldflags the -L flags of the libraries that configure
# found. In a cross build these were the sysroot and the buildlink tree in
# the work directory, so the target php85 package installed a php-config
# that names build machine paths. check-wrkref did not stop it: the default
# CHECK_WRKREF ("tools home cross") checks the tools and home directories
# and TOOLBASE, but neither the buildlink tree nor the sysroot.
# Require that a cross php85 rewrites ldflags in scripts/php-config after
# configure to the target library directory and its run path, then apply
# that rewrite to a php-config made from the distfile's
# scripts/php-config.in with the flags a cross configure records.
set -eu
[ "$#" -eq 3 ] || { echo "Usage: $0 PKGSRC MAKECONF NEW_WORK" >&2; exit 2; }
pkgsrc=$1 makeconf=$2 work=$3
[ ! -e "$work" ] || { echo "$0: $work exists" >&2; exit 2; }
pkg=$pkgsrc/lang/php85
bm() { MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$pkg" MAKECONF="$makeconf" "$@"; }
[ "$(bm -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
mkdir -p "$work/src"
bm WRKDIR="$work/wrk" -V '${_CROSS_DESTDIR}' -V '${BUILDLINK_DIR}' \
	-V '${WRKDIR}' -V '${LOCALBASE}' -V '${COMPILER_RPATH_FLAG}' \
	-V '${SUBST_CLASSES:Mcross-ldflags}' -V '${SUBST_STAGE.cross-ldflags}' \
	-V '${SUBST_FILES.cross-ldflags}' -V '${SUBST_SED.cross-ldflags}' \
	-V '${DISTDIR}/${DISTFILES:M*.tar.*}' -V '${DISTNAME}' > "$work/values"
{
	IFS= read -r sysroot; IFS= read -r buildlink; IFS= read -r wrkdir
	IFS= read -r localbase; IFS= read -r rpathflag; IFS= read -r class
	IFS= read -r stage; IFS= read -r files; IFS= read -r sedargs
	IFS= read -r distfile; IFS= read -r distname
} < "$work/values"
[ -n "$sysroot" ] || { echo "$0: the MAKECONF names no sysroot" >&2; exit 2; }
if [ -z "$class" ]; then
	echo "FAIL: a cross php85 installs php-config with the configure -L flags"
	exit 1
fi
status=0
fail() { echo "FAIL: $*"; status=1; }
[ "$stage" = post-configure ] || fail "the ldflags rewrite runs at $stage, not post-configure"
case " $files " in
*" scripts/php-config "*) ;;
*) fail "the ldflags rewrite does not edit scripts/php-config";;
esac

tar -xJf "$distfile" -C "$work/src" "$distname/scripts/php-config.in"
cfg=$work/src/$distname/scripts/php-config
sed -e "s,@prefix@,$localbase,g" -e "s,@exec_prefix@,$localbase,g" \
	-e "s,@PHP_LDFLAGS@, -L$sysroot$localbase/lib -L$sysroot/usr/lib -L$buildlink/lib,g" \
	-e "s,@EXTRA_LIBS@,-lreadline -lm,g" -e "s,@SED@,sed,g" \
	-e "s,@[A-Za-z_]*@,,g" "$cfg.in" > "$cfg.cross"
grep -q -e "-L$sysroot" "$cfg.cross" ||
	{ echo "$0: the stand-in php-config does not record the sysroot" >&2; exit 2; }
eval "sed $sedargs" < "$cfg.cross" > "$cfg"
expected="-L$localbase/lib $rpathflag$localbase/lib"
[ "$(sh "$cfg" --ldflags)" = "$expected" ] ||
	fail "php-config --ldflags is \"$(sh "$cfg" --ldflags)\", not \"$expected\""
if grep -n -e "$sysroot" -e "$wrkdir" "$cfg"; then
	fail "the installed php-config names the sysroot or the work directory"
fi
[ "$(sh "$cfg" --libs)" = "-lreadline -lm" ] || fail "php-config --libs changed"
[ -z "$(bm USE_CROSS_COMPILE=no -V '${SUBST_CLASSES:Mcross-ldflags}')" ] ||
	fail "a native php85 rewrites ldflags"
[ "$status" -eq 0 ] || exit 1
echo "PASS: the cross php85 php-config records only target library paths"

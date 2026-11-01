#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake apu-cross-config.sh PKGSRC MAKECONF APR_PACKAGE APU_PACKAGE
#
# A cross www/apache24 passed --with-apr=/usr/pkg and --with-apr-util=/usr/pkg,
# and www/serf passed APR=/usr/pkg/bin/apr-1-config,
# APU=/usr/pkg/bin/apu-1-config and OPENSSL=/usr/pkg/lib: target paths
# that the build host does not have, and SCons requires OPENSSL to be a
# directory. Stage the cross apr and apr-util binary packages as the target
# prefix, prepare the apr-1-config and apu-1-config copies for apache24 and
# run the queries of httpd's configure on them: APR_FIND_APR and
# APR_FIND_APU run "--help", then --apr-libtool must give a libtool that
# runs on the build host, and the include and link flags must name the
# target prefix and not the staged one. Also check that serf gets the same
# copies and the buildlink directory as OpenSSL install area, and that
# native builds keep the installed scripts. MAKECONF
# selects a cross build.
set -eu
[ "$#" -eq 4 ] ||
	{ echo "Usage: $0 PKGSRC MAKECONF APR_PACKAGE APU_PACKAGE" >&2; exit 2; }
pkgsrc=$1 makeconf=$2 aprpkg=$3 apupkg=$4
tmp=$(mktemp -d "${TMPDIR:-/tmp}/apu-config.XXXXXX")
trap 'rm -rf "$tmp"' EXIT
# The prepared cross tools name the selected sysroot, so keep CROSS_DESTDIR
# and point only the package paths (_CROSS_DESTDIR) at the staged prefix.
# The staged prefix has no package database: name the target LOCALBASE as
# the apr and apr-util prefix, where the sysroot package database puts it.
bm() {
	dir=$1 cross=$2; shift 2
	env MAKECONF="$makeconf" "${BMAKE:-bmake}" -C "$pkgsrc/$dir" \
	    MAKECONF="$makeconf" WRKOBJDIR="$tmp/w-$cross" \
	    _CROSS_DESTDIR="$tmp/sysroot" \
	    ${prefix:+BUILDLINK_PREFIX.apr=$prefix} \
	    ${prefix:+BUILDLINK_PREFIX.apr-util=$prefix} \
	    USE_CROSS_COMPILE=$cross "$@" </dev/null
}
prefix=
[ "$(bm www/apache24 yes -V '${USE_CROSS_COMPILE:Uno:tl}' 2>/dev/null)" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
prefix=$(bm www/apache24 yes -V '${LOCALBASE}' 2>/dev/null)
case $prefix in
/?*) ;;
*) echo "$0: no target LOCALBASE" >&2; exit 2;;
esac
mkdir -p "$tmp/sysroot$prefix"
tar -xzf "$aprpkg" -C "$tmp/sysroot$prefix" bin/apr-1-config libexec/apr
tar -xzf "$apupkg" -C "$tmp/sysroot$prefix" bin/apu-1-config
fail=0
apr=$(bm www/apache24 yes -V '${APR_CONFIG}' 2>/dev/null)
apu=$(bm www/apache24 yes -V '${APU_CONFIG}' 2>/dev/null)
[ -n "$apr" ] || { echo "FAIL: the cross apr buildlink3 file sets no APR_CONFIG"; fail=1; }
[ -n "$apu" ] || { echo "FAIL: the cross apr-util buildlink3 file sets no APU_CONFIG"; fail=1; }
args=$(bm www/apache24 yes -V '${CONFIGURE_ARGS:M--with-apr*}' 2>/dev/null)
if [ "$args" != "--with-apr=$apr --with-apr-util=$apu" ]; then
	echo "FAIL: cross apache24 configures $args, not the config copies"
	fail=1
fi
args=$(bm www/serf yes -V '${SCONS_BUILD_ARGS:MAP[RU]=*}' 2>/dev/null)
sapr=$(bm www/serf yes -V '${APR_CONFIG}' 2>/dev/null)
sapu=$(bm www/serf yes -V '${APU_CONFIG}' 2>/dev/null)
if [ -z "$sapr" ] || [ -z "$sapu" ] || [ "$args" != "APR=$sapr APU=$sapu" ]; then
	echo "FAIL: cross serf builds with $args, not the config copies"
	fail=1
fi
ssl=$(bm www/serf yes -V '${SCONS_BUILD_ARGS:MOPENSSL=*}' 2>/dev/null)
bl=$(bm www/serf yes -V '${BUILDLINK_DIR}' 2>/dev/null)
if [ -z "$bl" ] || [ "$ssl" != "OPENSSL=$bl" ]; then
	echo "FAIL: cross serf builds with $ssl, not the buildlink directory"
	fail=1
fi
[ "$fail" = 0 ] || exit 1
if ! bm www/apache24 yes apr-cross-config apu-cross-config >"$tmp/log" 2>&1; then
	echo "FAIL: preparing the cross config copies failed:"
	sed 's/^/  /' "$tmp/log" | tail -5
	exit 1
fi
# APR_FIND_APR and APR_FIND_APU: a config file is accepted if it runs
# with --help.
for c in "$apr" "$apu"; do
	if ! [ -x "$c" ] || ! "$c" --help >/dev/null 2>&1; then
		echo "FAIL: apache24 configure rejects $c"
		exit 1
	fi
done
# httpd's configure runs "$(apr-1-config --apr-libtool) --version".
lt=$("$apr" --apr-libtool)
if ! $lt --version >/dev/null 2>&1; then
	echo "FAIL: apr-1-config --apr-libtool gives $lt, which does not run"
	fail=1
fi
for q in --includes --includedir --bindir --ldflags \
    "--avoid-ldap --link-libtool --libs"; do
	# shellcheck disable=SC2086 # q holds several options
	out=$("$apu" $q)
	case $out in
	*"$tmp"*) echo "FAIL: apu-1-config $q names the staged prefix: $out"
		fail=1;;
	esac
done
case $("$apu" --includes) in
*"$prefix/include/apr-1"*) ;;
*) echo "FAIL: apu-1-config --includes lost the target include directory"; fail=1;;
esac
case " $("$apu" --avoid-ldap --link-libtool --libs) " in
*" -L$prefix/lib "*" -laprutil-1 "*) ;;
*) echo "FAIL: apu-1-config --link-libtool does not link the target libaprutil-1"
	fail=1;;
esac
prefix=
native=$(bm www/apache24 no -V '${CONFIGURE_ARGS:M--with-apr*}' 2>/dev/null)
napr=$(bm www/apache24 no -V '${BUILDLINK_PREFIX.apr}' 2>/dev/null)
napu=$(bm www/apache24 no -V '${BUILDLINK_PREFIX.apr-util}' 2>/dev/null)
if [ "$native" != "--with-apr=$napr/bin/apr-1-config --with-apr-util=$napu/bin/apu-1-config" ]; then
	echo "FAIL: native apache24 configures $native"
	fail=1
fi
native=$(bm www/serf no -V '${SCONS_BUILD_ARGS:MAP[RU]=*}' 2>/dev/null)
if [ "$native" != "APR=$napr/bin/apr-1-config APU=$napu/bin/apu-1-config" ]; then
	echo "FAIL: native serf builds with $native"
	fail=1
fi
native=$(bm www/serf no -V '${SCONS_BUILD_ARGS:MOPENSSL=*}' 2>/dev/null)
bl=$(bm www/serf no -V '${BUILDLINK_DIR}' 2>/dev/null)
if [ "$native" != "OPENSSL=$bl" ]; then
	echo "FAIL: native serf builds with $native"
	fail=1
fi
[ "$fail" = 0 ] || exit 1
echo "PASS: cross apache24 and serf run host apr-1-config and apu-1-config copies; native unchanged"

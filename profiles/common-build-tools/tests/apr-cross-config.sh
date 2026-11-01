#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake apr-cross-config.sh PKGSRC MAKECONF APR_PACKAGE
#
# A cross devel/apr-util passed the target path /usr/pkg/bin/apr-1-config
# to configure, which the build host does not have, and configure stopped
# at "the --with-apr parameter is incorrect". Stage the cross apr binary
# package APR_PACKAGE as the target prefix, prepare the apr-1-config copy
# for devel/apr-util and apply the checks of apr-util's configure to it:
# APR_FIND_APR runs "--with-apr --help", and apu-conf.m4 copies
# apr_rules.mk from --installbuilddir. The rules must name the cross
# libtool and nothing under the staged target prefix or /usr/pkg. Also
# check that configure gets that copy, and that a native build keeps the
# installed apr-1-config. MAKECONF selects a cross build.
set -eu
[ "$#" -eq 3 ] || { echo "Usage: $0 PKGSRC MAKECONF APR_PACKAGE" >&2; exit 2; }
pkgsrc=$1 makeconf=$2 package=$3
tmp=$(mktemp -d "${TMPDIR:-/tmp}/apr-config.XXXXXX")
trap 'rm -rf "$tmp"' EXIT
# The prepared cross tools name the selected sysroot, so keep CROSS_DESTDIR
# and point only the package paths (_CROSS_DESTDIR) at the staged prefix.
# The staged prefix has no package database: name the target LOCALBASE as
# the apr prefix, where the sysroot package database puts it.
bm() {
	cross=$1; shift
	env MAKECONF="$makeconf" "${BMAKE:-bmake}" -C "$pkgsrc/devel/apr-util" \
	    MAKECONF="$makeconf" WRKOBJDIR="$tmp/w-$cross" \
	    _CROSS_DESTDIR="$tmp/sysroot" ${prefix:+BUILDLINK_PREFIX.apr=$prefix} \
	    USE_CROSS_COMPILE=$cross "$@" </dev/null
}
prefix=
[ "$(bm yes -V '${USE_CROSS_COMPILE:Uno:tl}' 2>/dev/null)" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
prefix=$(bm yes -V '${LOCALBASE}' 2>/dev/null)
case $prefix in
/?*) ;;
*) echo "$0: no target LOCALBASE" >&2; exit 2;;
esac
mkdir -p "$tmp/sysroot$prefix"
tar -xzf "$package" -C "$tmp/sysroot$prefix" bin/apr-1-config libexec/apr
fail=0
args=$(bm yes -V '${CONFIGURE_ARGS:M--with-apr=*:S/^--with-apr=//}' 2>/dev/null)
cfg=$(bm yes -V '${APR_CONFIG}' 2>/dev/null)
libtool=$(bm yes -V '${PKG_LIBTOOL}' 2>/dev/null)
if [ "$args" != "$cfg" ] || [ -z "$cfg" ]; then
	echo "FAIL: cross apr-util configures --with-apr=$args, not the apr-1-config copy"
	fail=1
fi
if ! bm yes apr-cross-config >"$tmp/log" 2>&1; then
	echo "FAIL: preparing the cross apr-1-config copy failed:"
	sed 's/^/  /' "$tmp/log" | tail -5
	exit 1
fi
# APR_FIND_APR: an apr-config file is accepted if it runs with --help.
if ! [ -x "$args" ] || ! "$args" --help >/dev/null 2>&1; then
	echo "FAIL: apr-util configure rejects --with-apr=$args"
	exit 1
fi
# apu-conf.m4: cd to --installbuilddir and copy apr_rules.mk from there.
dir=$("$args" --installbuilddir)
if ! (cd "$dir" 2>/dev/null) || ! [ -f "$dir/apr_rules.mk" ]; then
	echo "FAIL: apr-1-config --installbuilddir gives $dir without apr_rules.mk"
	exit 1
fi
for v in apr_builddir apr_builders top_builddir; do
	if ! grep -qx "$v=$dir" "$dir/apr_rules.mk"; then
		echo "FAIL: copied apr_rules.mk: $(grep "^$v=" "$dir/apr_rules.mk")"
		fail=1
	fi
done
if [ "$(readlink "$dir/libtool")" != "$libtool" ]; then
	echo "FAIL: the apr build directory libtool is not the cross libtool $libtool"
	fail=1
fi
for f in make_exports.awk make_var_export.awk mkdir.sh; do
	[ -f "$dir/$f" ] || { echo "FAIL: $dir/$f is missing"; fail=1; }
done
if grep -n "$tmp/sysroot\|/usr/pkg/libexec" "$dir/apr_rules.mk"; then
	echo "FAIL: copied apr_rules.mk names the target prefix"
	fail=1
fi
case $("$args" --includes) in
*"$prefix/include/apr-1"*) ;;
*) echo "FAIL: apr-1-config --includes lost the target include directory"; fail=1;;
esac
prefix=
native=$(bm no -V '${CONFIGURE_ARGS:M--with-apr=*}' 2>/dev/null)
nprefix=$(bm no -V '${BUILDLINK_PREFIX.apr}' 2>/dev/null)
if [ "$native" != "--with-apr=$nprefix/bin/apr-1-config" ]; then
	echo "FAIL: native apr-util configures $native"
	fail=1
fi
[ "$fail" = 0 ] || exit 1
echo "PASS: cross apr-util runs a host apr-1-config copy with its build directory; native unchanged"

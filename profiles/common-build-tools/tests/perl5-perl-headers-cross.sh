#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake perl5-perl-headers-cross.sh PKGSRC MAKECONF TARGET_CC NEW_WORK
#
# A cross p5-perl-headers ran the target /usr/pkg/bin/h2ph in the build
# host's /usr/include. Require that the recipe reads the sysroot headers and
# runs the build Perl's h2ph with the target build context, then run that
# command on target headers and require target compiler symbols, and no
# host ones, in _h2ph_pre.ph.
set -eu
[ "$#" -eq 4 ] || { echo "Usage: $0 PKGSRC MAKECONF TARGET_CC NEW_WORK" >&2; exit 2; }
pkgsrc=$1 makeconf=$2 cc=$3
case "$4" in /*) ;; *) echo "$0: NEW_WORK must be absolute" >&2; exit 2;; esac
mkdir "$4"
work=$4
bm() { dir=$1; shift; MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$pkgsrc/$dir" MAKECONF="$makeconf" "$@"; }
pkg=devel/p5-perl-headers
set -- $(bm $pkg -V '${USE_CROSS_COMPILE:Uno:tl}' -V '${EMBERBSD_CROSS_BUILD_PERL}' \
	-V '${EMBERBSD_CROSS_BUILD_PYTHON}' -V '${EMBERBSD_PERL_TARGET_CONFIG}' \
	-V '${EMBERBSD_CROSS_SYSROOT}')
[ "$1" = yes ] || { echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
host=$2 python=$3 target=$4 sysroot=$5
status=0
[ -z "$(bm $pkg -V '${PKG_FAIL_REASON}')" ] || { echo "FAIL: $pkg is refused"; status=1; }
inc=$(bm $pkg -V '${USR_INCLUDE}')
[ "$inc" = "$sysroot/usr/include" ] || { echo "FAIL: headers come from $inc"; status=1; }
h2ph=$(bm $pkg WRKDIR="$work" -V '${_P5PH_H2PH}')
sed_expr=$(bm $pkg -V '${_P5PH_TARGET_CONFIG_SED}')
case "$h2ph" in
*" $host $work/h2ph-target") ;;
*) echo "FAIL: h2ph command is '$h2ph'"; status=1;;
esac
[ "$status" -eq 0 ] || exit 1
"$python" -B "$pkgsrc/lang/perl5/files/prepare-build-config.py" --host-perl "$host" \
	--target-config "$target" --sysroot "$sysroot" --cc "$cc" --ld "$cc" \
	--ar "${cc%clang}ar" --ranlib "${cc%clang}ranlib" --cflags=-O2 --ldflags= \
	--output "$work/ember-perl-build-config.json"
sed -e "$sed_expr" "$(dirname "$host")/h2ph" > "$work/h2ph-target"
mkdir "$work/out"
(cd "$inc" && eval "$h2ph -d \"\$work/out\" sys/errno.h") > "$work/h2ph.log"
pre=$work/out/_h2ph_pre.ph
for sym in __NetBSD__ __aarch64__; do
	grep -q "sub $sym()" "$pre" || { echo "FAIL: _h2ph_pre.ph lacks $sym"; status=1; }
done
for sym in __APPLE__ __MACH__; do
	if grep -q "sub $sym()" "$pre"; then echo "FAIL: _h2ph_pre.ph defines host $sym"; status=1; fi
done
grep -q 'EPERM' "$work/out/sys/errno.ph" || { echo "FAIL: sys/errno.ph lacks EPERM"; status=1; }
[ "$status" -eq 0 ] && echo PASS
exit "$status"

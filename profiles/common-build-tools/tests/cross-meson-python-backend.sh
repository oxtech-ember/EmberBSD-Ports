#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake cross-meson-python-backend.sh PKGSRC MAKECONF
#
# meson-python starts "meson setup" itself with only the -Csetup-args from
# WHEEL_ARGS. Without a cross file Meson configured graphics/py-cairo as a
# native build and failed to run the target compiler's sanity check program.
# Run meson setup on a C project with the setup arguments of the
# graphics/py-cairo wheel build, the Meson cross file it names, and the
# wrapped target compiler of archivers/bzip2 (C only, no dependencies).
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
pkgsrc=$1 makeconf=$2
bm() { r=$1; shift; MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$pkgsrc/$r" MAKECONF="$makeconf" "$@"; }
[ "$(bm archivers/bzip2 -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] && [ "$(bm archivers/bzip2 -V '${OPSYS}')" = NetBSD ] ||
	{ echo "$0: select a MAKECONF for a NetBSD cross build" >&2; exit 2; }
meson=$(bm archivers/bzip2 -V '${TOOLBASE}/bin/meson')
make_env=$(bm archivers/bzip2 -V '${MAKE_ENV}')
tmp=$(mktemp -d "${TMPDIR:-/tmp}/meson-backend.XXXXXX")
trap 'rm -rf "$tmp"; bm archivers/bzip2 clean >/dev/null 2>&1 || :' EXIT
bm archivers/bzip2 clean >/dev/null 2>&1 || :
bm archivers/bzip2 wrapper >/dev/null 2>&1 || { echo "FAIL: wrapper"; exit 1; }
mkdir "$tmp/w" "$tmp/src"
setup_args=
for a in $(bm graphics/py-cairo WRKDIR="$tmp/w" -V '${WHEEL_ARGS}'); do
	case $a in -Csetup-args=*) setup_args="$setup_args ${a#-Csetup-args=}";; esac
done
case $setup_args in *--cross-file=*)
	bm graphics/py-cairo WRKDIR="$tmp/w" "$tmp/w/.meson_cross" >"$tmp/cross.log" 2>&1 ||
		{ tail -5 "$tmp/cross.log"; echo "FAIL: Meson cross file"; exit 1; };;
esac
printf "project('backend', 'c')\nexecutable('probe', 'probe.c')\n" >"$tmp/src/meson.build"
printf 'int main(void) { return 0; }\n' >"$tmp/src/probe.c"
status=0
eval "env $make_env \"\$meson\" setup $setup_args \"\$tmp/src\" \"\$tmp/build\"" \
	>"$tmp/setup.log" 2>&1 || { grep -m 3 'ERROR' "$tmp/setup.log"; status=1; }
grep -q '^Build type: cross build' "$tmp/setup.log" ||
	{ echo "FAIL: $(grep -m 1 '^Build type:' "$tmp/setup.log" || echo 'no build type')"; status=1; }
grep -q "^Host machine cpu family: $(bm graphics/py-cairo -V '${MESON_CPU_FAMILY}')\$" "$tmp/setup.log" ||
	{ echo "FAIL: host machine is not the target"; status=1; }
[ "$status" -eq 0 ] || exit 1
echo "PASS: meson-python wheel builds configure Meson for the cross target"

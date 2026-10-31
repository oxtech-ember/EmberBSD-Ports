#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake python-cross-configure-env.sh PKGSRC MAKECONF
#
# AX_PYTHON_DEVEL in GNU configure scripts asks the build machine Python
# for the include path, libraries and link flags. Without the cross
# PYTHONPATH it read the build machine's sysconfig, so textproc/libplist
# linked its Python probe with "-framework CoreFoundation" on macOS and
# configure gave up. Run the Python of libplist's CONFIGURE_ENV as
# configure does, and check that a Meson recipe (math/py-numpy) keeps the
# plain environment: Meson itself runs on that interpreter.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
pkgsrc=$1 makeconf=$2
tmp=$(mktemp -d "${TMPDIR:-/tmp}/python-configure-env.XXXXXX")
trap 'rm -rf "$tmp"' EXIT
bm() { dir=$1; shift; MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$pkgsrc/$dir" \
	MAKECONF="$makeconf" SKIP_DEPENDS=yes WRKDIR="$tmp/w" "$@"; }
[ "$(bm textproc/libplist -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
mkdir -p "$tmp/w"
bm textproc/libplist "$tmp/w/.pysite/sitecustomize.py" >"$tmp/site.log" 2>&1 ||
	{ tail -5 "$tmp/site.log"; echo "FAIL: sitecustomize.py"; exit 1; }
env=$(bm textproc/libplist -V '${CONFIGURE_ENV:M*PYTHON*}')
python=$(bm textproc/libplist -V '${TOOL_PYTHONBIN}')
localbase=$(bm textproc/libplist -V '${LOCALBASE}')
status=0
got=$(eval "env $env \"\$python\"" -c \
	"'import sys, sysconfig; print(sys.platform, sysconfig.get_config_var(\"LIBDIR\"), \"-framework\" in (sysconfig.get_config_var(\"LINKFORSHARED\") or \"\"))'")
case $got in
netbsd*" $localbase/lib False") ;;
*) echo "FAIL: configure Python reports '$got'"; status=1 ;;
esac
case " $(bm math/py-numpy -V '${CONFIGURE_ENV}') " in
*" PYTHONPATH="*) echo "FAIL: the Meson recipe gets the cross PYTHONPATH"; status=1 ;;
esac
[ "$status" -eq 0 ] || exit 1
echo "PASS: GNU configure scripts read the target Python settings"

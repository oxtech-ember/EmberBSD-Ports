#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake cross-config-paths.sh PKGSRC MAKECONF
#
# numpy/__config__.py records the Python that ran Meson and the BLAS and
# LAPACK directories from pkg-config. In a cross build these are the build
# machine Python under TOOLBASE and directories in the sysroot, so the
# work-directory reference check stopped the cross package. Install a
# __config__.py with the build paths in the recipe's DESTDIR, run the
# recipe's post-install substitution, and require the target Python and
# target prefix, with no build machine path left.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
recipe=$1/math/py-numpy makeconf=$2
tmp=$(mktemp -d "${TMPDIR:-/tmp}/numpy-config.XXXXXX")
trap 'rm -rf "$tmp"' EXIT
bm() { MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$recipe" MAKECONF="$makeconf" \
	SKIP_DEPENDS=yes WRKDIR="$tmp/w" "$@" </dev/null; }
[ "$(bm -V '${USE_CROSS_COMPILE:Uno:tl}' 2>/dev/null)" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
v() { bm -V "\${$1}" 2>/dev/null; }
buildpy=$(v TOOL_PYTHONBIN) targetpy=$(v PYTHONBIN) sysroot=$(v _CROSS_DESTDIR)
prefix=$(v PREFIX) toolbase=$(v TOOLBASE)
case $buildpy:$sysroot in
/?*:/?*) ;;
*) echo "$0: no build Python or sysroot" >&2; exit 2 ;;
esac
[ "$buildpy" != "$targetpy" ] || { echo "$0: build and target Python are the same" >&2; exit 2; }
cfg=$(v DESTDIR)$prefix/$(v PYSITELIB)/numpy/__config__.py
mkdir -p "$(v WRKSRC)" "$(dirname "$cfg")"
# The lines of the __config__.py that numpy 2.5.3 installs in a cross build.
cat > "$cfg" <<CFG
CONFIG = _cleanup(
    {
        "Build Dependencies": {
            "blas": {
                "include directory": r"$sysroot$prefix/include/netlib",
                "lib directory": r"$sysroot$prefix/lib",
                "pc file directory": r"$sysroot$prefix/lib/pkgconfig",
            },
        },
        "Python Information": {
            "path": r"$buildpy",
            "version": "3.15",
        },
    }
)
CFG
if ! bm subst-crossconfig >"$tmp/log" 2>&1; then
	echo "FAIL: the recipe has no cross substitution for numpy/__config__.py"
	exit 1
fi
fail=0
for ref in "$toolbase" "$sysroot"; do
	if grep -F -- "$ref" "$cfg" >/dev/null; then
		echo "FAIL: __config__.py still names $ref:"
		grep -F -- "$ref" "$cfg" | sed 's/^/  /'
		fail=1
	fi
done
grep -F "\"path\": r\"$targetpy\"," "$cfg" >/dev/null ||
	{ echo "FAIL: __config__.py does not name the target Python $targetpy"; fail=1; }
grep -F "\"include directory\": r\"$prefix/include/netlib\"," "$cfg" >/dev/null ||
	{ echo "FAIL: __config__.py lost the target BLAS include directory"; fail=1; }
[ "$fail" = 0 ] || exit 1
echo "PASS: cross numpy/__config__.py names $targetpy and $prefix"

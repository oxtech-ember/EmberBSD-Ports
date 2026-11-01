#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake py-pygraphviz-abi3.sh PKGSRC MAKECONF [SITELIB]
#
# pygraphviz 2.0.4 builds its SWIG module against the Python stable ABI
# (Py_LIMITED_API 3.10), so setuptools installs _graphviz.abi3.so instead
# of _graphviz.so, and the sdist no longer ships the SWIG-generated
# graphviz.py. Check that the recipe is at least 2.0.4 without a leftover
# PKGREVISION, that PLIST lists the abi3 module and graphviz.py, and that
# distinfo covers the distfile. With SITELIB (a site-packages directory
# that holds an installed pygraphviz for ${PYTHON:-python3}), also import
# it, check its version and module name, and lay out a small graph.
set -eu
[ "$#" -eq 2 ] || [ "$#" -eq 3 ] ||
	{ echo "Usage: $0 PKGSRC MAKECONF [SITELIB]" >&2; exit 2; }
pkgsrc=$1 makeconf=$2 sitelib=${3:-}
pkg=$pkgsrc/graphics/py-pygraphviz
tmp=$(mktemp -d "${TMPDIR:-/tmp}/pygraphviz-abi3.XXXXXX")
trap 'rm -rf "$tmp"' EXIT
fail() { echo "FAIL: $*" >&2; exit 1; }
# Succeed when dotted version $1 is at least $2.
vge() {
	awk -v a="$1" -v b="$2" 'BEGIN { n = split(a, x, "."); m = split(b, y, ".")
		for (i = 1; i <= (n > m ? n : m); i++) {
			if (x[i] + 0 > y[i] + 0) exit 0
			if (x[i] + 0 < y[i] + 0) exit 1 }
		exit 0 }'
}
bm() {
	env MAKECONF="$makeconf" "${BMAKE:-bmake}" -C "$pkg" \
	    MAKECONF="$makeconf" WRKOBJDIR="$tmp/w" _MAKEVARS_MK=defined \
	    -V "$1" </dev/null 2>/dev/null
}
version=$(bm '${PKGVERSION_NOREV}')
[ -n "$version" ] || fail "cannot read the py-pygraphviz version"
vge "$version" 2.0.4 || fail "py-pygraphviz $version is older than 2.0.4"
[ -z "$(bm '${PKGREVISION}')" ] ||
	fail "PKGREVISION is still set after the update to $version"
distfile=$(bm '${DISTFILES}')
grep -q "^SHA512 ($distfile) = " "$pkg/distinfo" ||
	fail "distinfo has no SHA512 for $distfile"
grep -q '^${PYSITELIB}/pygraphviz/_graphviz\.abi3\.so$' "$pkg/PLIST" ||
	fail "PLIST does not list the stable ABI module _graphviz.abi3.so"
! grep -q '^${PYSITELIB}/pygraphviz/_graphviz\.so$' "$pkg/PLIST" ||
	fail "PLIST still lists _graphviz.so"
grep -q '^${PYSITELIB}/pygraphviz/graphviz\.py$' "$pkg/PLIST" ||
	fail "PLIST does not list the SWIG-generated graphviz.py"
[ -n "$sitelib" ] || { echo PASS; exit 0; }
case $sitelib in /*) ;; *) fail "SITELIB must be absolute" ;; esac
cd "$tmp"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$sitelib "${PYTHON:-python3}" - "$version" <<'PY' ||
import os, sys
import pygraphviz, pygraphviz._graphviz as module
if pygraphviz.__version__ != sys.argv[1]:
    sys.exit("FAIL: pygraphviz reports %s" % pygraphviz.__version__)
if not os.path.basename(module.__file__).startswith("_graphviz.abi3"):
    sys.exit("FAIL: imported %s, not the abi3 module" % module.__file__)
graph = pygraphviz.AGraph(directed=True)
graph.add_edges_from([("a", "b"), ("b", "c"), ("a", "c")])
graph.layout("dot")
svg = graph.draw(format="svg").decode()
if svg.count('class="node"') != 3:
    sys.exit("FAIL: dot did not lay out the three nodes")
if pygraphviz.AGraph(string=graph.string()).number_of_edges() != 3:
    sys.exit("FAIL: the graph does not read back")
PY
	fail "pygraphviz from $sitelib does not import or lay out a graph"
echo PASS

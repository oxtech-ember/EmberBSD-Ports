#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake graphviz-version-sfdp.sh PKGSRC MAKECONF [PREFIX]
#
# graphviz 15.1.1 aborts in sfdp on small graphs ("free(): invalid next
# size", upstream issue 2852) and crashes in orthogonal routing. 16.1.0
# fixes both, and 16.0.0 bumped the libcgraph and libxdot sonames. Check
# that the recipe is at least 16.1.0 and that buildlink3.mk asks for the
# new ABI. With PREFIX (an installed or staged graphviz prefix), also check
# that dot reports the recipe version, that dot writes SVG and PNG, and
# that sfdp lays out the graph from issue 2852.
set -eu
[ "$#" -eq 2 ] || [ "$#" -eq 3 ] ||
	{ echo "Usage: $0 PKGSRC MAKECONF [PREFIX]" >&2; exit 2; }
pkgsrc=$1 makeconf=$2 prefix=${3:-}
tmp=$(mktemp -d "${TMPDIR:-/tmp}/graphviz-sfdp.XXXXXX")
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
version=$(env MAKECONF="$makeconf" "${BMAKE:-bmake}" -C "$pkgsrc/graphics/graphviz" \
    MAKECONF="$makeconf" WRKOBJDIR="$tmp/w" _MAKEVARS_MK=defined \
    -V '${PKGVERSION_NOREV}' </dev/null 2>/dev/null)
[ -n "$version" ] || fail "cannot read the graphviz version"
vge "$version" 16.1.0 || fail "graphviz $version is older than 16.1.0"
abi=$(sed -n 's/^BUILDLINK_ABI_DEPENDS\.graphviz+=[[:space:]]*graphviz>=//p' \
    "$pkgsrc/graphics/graphviz/buildlink3.mk")
[ -n "$abi" ] && vge "$abi" 16.0.0 ||
	fail "buildlink3.mk does not require the libcgraph.10/libxdot.5 ABI (graphviz>=${abi:-?})"
[ -n "$prefix" ] || { echo PASS; exit 0; }
case $prefix in /*) ;; *) fail "PREFIX must be absolute" ;; esac
# Run from a copy of the plugin directory so dot -c does not write into
# PREFIX, and load the libraries of this prefix.
cp -R "$prefix/lib/graphviz" "$tmp/plugins"
GVBINDIR=$tmp/plugins DYLD_LIBRARY_PATH=$prefix/lib LD_LIBRARY_PATH=$prefix/lib
export GVBINDIR DYLD_LIBRARY_PATH LD_LIBRARY_PATH
"$prefix/bin/dot" -c || fail "dot -c cannot register the plugins"
"$prefix/bin/dot" -V 2>&1 | grep -q "graphviz version $version " ||
	fail "dot does not report graphviz $version"
echo 'digraph G { a -> b -> c; a -> c; }' > "$tmp/small.dot"
"$prefix/bin/dot" -Tsvg -o "$tmp/small.svg" "$tmp/small.dot" ||
	fail "dot -Tsvg failed"
grep -q '<svg' "$tmp/small.svg" || fail "dot -Tsvg wrote no SVG"
"$prefix/bin/dot" -Tpng -o "$tmp/small.png" "$tmp/small.dot" ||
	fail "dot -Tpng failed"
[ "$(od -An -tx1 -N4 "$tmp/small.png" | tr -d ' \n')" = 89504e47 ] ||
	fail "dot -Tpng wrote no PNG"
cat > "$tmp/sfdp.dot" <<'GRAPH'
digraph {
  n0 -> n1; n0 -> n2; n0 -> n3; n0 -> n4; n0 -> n5; n0 -> n6;
  n0 -> n7; n0 -> n8; n0 -> n9; n0 -> n10; n0 -> n11; n0 -> n12;
  n13 -> n14; n13 -> n7;
  n15 -> n16; n15 -> n17; n15 -> n18;
  n19 -> n20; n19 -> n21; n19 -> n18; n19 -> n2; n19 -> n22; n19 -> n23;
}
GRAPH
"$prefix/bin/sfdp" -Tsvg -o "$tmp/sfdp.svg" "$tmp/sfdp.dot" ||
	fail "sfdp failed on the graph from upstream issue 2852"
[ "$(grep -c 'class="node"' "$tmp/sfdp.svg")" -eq 24 ] ||
	fail "sfdp did not lay out all 24 nodes"
echo PASS

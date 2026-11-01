#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake graphviz-native-darwin-libraries.sh PKGSRC MAKECONF
#
# A native Darwin package records its libraries from Mach-O load commands
# (MACHO_USE_LOAD_COMMANDS), and each one must belong to a declared
# dependency. graphviz@native failed that check: its render and gts plugins
# call cairo and glib2, which came only through pango and gts; dot_builtins
# linked the libraries of libtool dependency_libs (libgd.la, libfreetype.la);
# and the gd plugin added the gd image libraries. Check that graphviz
# declares cairo and glib2 directly, and that native Darwin builds drop
# unused dylibs and leave gd out.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
pkgsrc=$1 makeconf=$2
tmp=$(mktemp -d "${TMPDIR:-/tmp}/graphviz-libs.XXXXXX")
trap 'rm -rf "$tmp"' EXIT
bm() {
	cross=$1; shift
	env MAKECONF="$makeconf" "${BMAKE:-bmake}" -C "$pkgsrc/graphics/graphviz" \
	    MAKECONF="$makeconf" WRKOBJDIR="$tmp/w" USE_CROSS_COMPILE=$cross \
	    _MAKEVARS_MK=defined "$@" </dev/null 2>/dev/null
}
fail() { echo "FAIL: $*" >&2; exit 1; }
# Print the buildlink3 packages graphviz includes itself.
direct() {
	bm "$1" -V '${BUILDLINK_TREE}' | tr ' ' '\n' |
	    awk '/^-/ { d--; next } { if (d == 0) print; d++ }'
}
for c in yes no; do
	for p in cairo glib2; do
		direct $c | grep -qx "$p" ||
			fail "USE_CROSS_COMPILE=$c: $p is not a direct dependency"
	done
done
[ "$(bm no -V '${OPSYS}')" = Darwin ] ||
	{ echo "SKIP: the native checks need a Darwin build host"; exit 0; }
bm no -V '${LDFLAGS}' | tr ' ' '\n' | grep -qx -- -Wl,-dead_strip_dylibs ||
	fail "native LDFLAGS do not drop unused dylibs"
bm no -V '${PKG_OPTIONS}' | tr ' ' '\n' | grep -qx gd &&
	fail "native PKG_OPTIONS enable gd"
bm no -V '${CONFIGURE_ARGS}' | tr ' ' '\n' | grep -qx -- --without-libgd ||
	fail "native configure does not disable libgd"
echo PASS

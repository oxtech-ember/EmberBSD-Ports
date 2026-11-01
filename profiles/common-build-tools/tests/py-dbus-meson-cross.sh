#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake py-dbus-meson-cross.sh PKGSRC MAKECONF [DESTDIR]
#
# py-dbus stayed at dbus-python 1.3.2, whose UnixFd_dealloc closed the
# descriptor but never freed the object (fixed in 1.5.1, dbus-python#62).
# dbus-python 1.5 builds only with Meson. Check that py-dbus and
# dbus-python-common select the same release, at least 1.5.1, and that a
# cross build runs Meson with the build machine Python and without the
# docs or tests. With DESTDIR, the staged directory of a py-dbus build,
# also check that it installed both extension modules built for the
# target and that _dbus_bindings reports the PKGNAME version.
set -eu
[ "$#" -eq 2 ] || [ "$#" -eq 3 ] ||
	{ echo "Usage: $0 PKGSRC MAKECONF [DESTDIR]" >&2; exit 2; }
pkgsrc=$1 makeconf=$2 destdir=${3-}
fail() { echo "FAIL: $*" >&2; exit 1; }
bm() {
	dir=$1; shift
	env MAKECONF="$makeconf" "${BMAKE:-bmake}" -C "$pkgsrc/sysutils/$dir" \
	    MAKECONF="$makeconf" _MAKEVARS_MK=defined "$@" </dev/null 2>/dev/null
}
[ "$(bm py-dbus -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
# Print 1 if version $1 is older than $2.
older() {
	awk -v a="$1" -v b="$2" 'BEGIN {
		n = split(a, x, "."); m = split(b, y, ".")
		for (i = 1; i <= (n > m ? n : m); i++) {
			if (x[i] + 0 < y[i] + 0) { print 1; exit }
			if (x[i] + 0 > y[i] + 0) { print 0; exit }
		}
		print 0 }'
}
version=$(bm py-dbus -V '${PKGVERSION_NOREV}')
[ "$(older "$version" 1.5.1)" = 0 ] ||
	fail "py-dbus $version lacks the UnixFd memory leak fix of 1.5.1"
[ "$(bm py-dbus -V '${DISTNAME}')" = "$(bm dbus-python-common -V '${DISTNAME}')" ] ||
	fail "py-dbus and dbus-python-common use different releases"
for dir in py-dbus dbus-python-common; do
	args=$(bm $dir -V '${MESON_ARGS}' | tr ' ' '\n')
	[ -n "$(bm $dir -V '${MESON_REQD}')" ] || fail "$dir does not build with Meson"
	python=$(printf '%s\n' "$args" | sed -n 's/^-Dpython=//p')
	[ -n "$python" ] || fail "$dir does not select the Meson Python"
	"$python" -c 'import sys; sys.exit(sys.hexversion < 0x3070000)' >/dev/null 2>&1 ||
		fail "$dir: Meson cannot run -Dpython=$python on the build machine"
	for opt in -Ddoc=disabled -Dtests=disabled; do
		printf '%s\n' "$args" | grep -qx -- "$opt" || fail "$dir lacks $opt"
	done
done
# dbus-python-common installs no module; building them needs a target Python.
[ -z "$(bm dbus-python-common -V '${BUILD_DIRS}')" ] ||
	fail "dbus-python-common builds the extension modules"
if [ -n "$destdir" ]; then
	site=$destdir$(bm py-dbus -V '${PREFIX}/${PYSITELIB}')
	for m in _dbus_bindings _dbus_glib_bindings; do
		set -- "$site/$m"*.so
		[ -f "$1" ] || fail "$m was not installed in $site"
		file -b "$1" | grep -q "^ELF.*$(bm py-dbus -V '${MESON_CPU_FAMILY}')" ||
			fail "$m is not a target module: $(file -b "$1")"
	done
	strings "$site/_dbus_bindings"*.so | grep -qx "$version" ||
		fail "_dbus_bindings does not report version $version"
fi
echo "PASS: py-dbus $version builds with Meson for cross targets"

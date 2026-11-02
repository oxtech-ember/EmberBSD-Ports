#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). pybind11 cross pkg-config regression.
# Configures graphics/py-contourpy, a meson consumer of pybind11, for the
# cross target and asks its pkg-config tool for pybind11. The installed
# site-packages pybind11.pc is not in the buildlink pkg-config path.
set -eu
[ "$#" = 4 ] || { echo "Usage: $0 BMAKE CROSS_MAKECONF EXPORTED_PKGSRC NEW_WORKOBJDIR" >&2; exit 2; }
bmake=$1 conf=$2 pkgsrc=$3 work=$4
for path in "$bmake" "$conf" "$pkgsrc" "$work"; do
    case "$path" in /*) ;; *) echo 'Use absolute paths' >&2; exit 2;; esac
done
mkdir "$work"
mk() { MAKECONF=$conf "$bmake" -C "$pkgsrc/graphics/py-contourpy" MAKECONF="$conf" WRKOBJDIR="$work" "$@" </dev/null; }
fail() { echo "FAIL: $*" >&2; exit 1; }
[ "$(mk show-var VARNAME=USE_CROSS_COMPILE | tr A-Z a-z)" = yes ] || { echo 'CROSS_MAKECONF must select a cross build' >&2; exit 2; }
mk configure >"$work/configure.log" 2>&1 || fail "configure failed; see $work/configure.log"
wrkdir=$(mk show-var VARNAME=WRKDIR)
bl=$(mk show-var VARNAME=BUILDLINK_DIR)
site=$(mk show-var VARNAME=PYSITELIB)
pc=$wrkdir/.tools/bin/pkg-config
[ -x "$pc" ] || fail 'the pkg-config tool is not enabled'
[ -f "$bl/lib/pkgconfig/pybind11.pc" ] || fail 'pybind11.pc is missing from the buildlink pkg-config directory'
inc=$("$pc" --cflags-only-I pybind11) || fail 'pkg-config cannot find pybind11'
case "$inc" in
    */"$site"/pybind11/include*) ;;
    *) fail "unexpected pybind11 include flags: $inc" ;;
esac
[ -f "$bl/$site/pybind11/include/pybind11/pybind11.h" ] || fail 'pybind11 headers missing from the buildlink tree'
version=$("$pc" --modversion pybind11)
[ "$version" = "$(sed -n 's/^Version: //p' "$bl/$site/pybind11/share/pkgconfig/pybind11.pc")" ] || fail "version mismatch: $version"
# Without the copy, the pkg-config tool finds no pybind11.
mv "$bl/lib/pkgconfig/pybind11.pc" "$work/pybind11.pc.saved"
if "$pc" --exists pybind11; then fail 'pybind11 was found without the buildlink copy'; fi
mv "$work/pybind11.pc.saved" "$bl/lib/pkgconfig/pybind11.pc"
echo "PASS: pkg-config finds pybind11 $version through the buildlink copy only"

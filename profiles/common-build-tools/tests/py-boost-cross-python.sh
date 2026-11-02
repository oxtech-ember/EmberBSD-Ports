#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Boost.Python cross configuration regression.
# Configures devel/py-boost for the NetBSD cross target, then asks b2 for a
# dry run. The generated user-config.jam must select Boost.Python and
# Boost.NumPy for <target-os>netbsd; the upstream one must not.
set -eu
[ "$#" = 4 ] || { echo "Usage: $0 BMAKE CROSS_MAKECONF EXPORTED_PKGSRC NEW_WORKOBJDIR" >&2; exit 2; }
bmake=$1 conf=$2 pkgsrc=$3 work=$4
for path in "$bmake" "$conf" "$pkgsrc" "$work"; do
    case "$path" in /*) ;; *) echo 'Use absolute paths' >&2; exit 2;; esac
done
mkdir "$work"
mk() { MAKECONF=$conf "$bmake" -C "$pkgsrc/devel/py-boost" MAKECONF="$conf" WRKOBJDIR="$work" "$@" </dev/null; }
[ "$(mk show-var VARNAME=USE_CROSS_COMPILE | tr A-Z a-z)" = yes ] || { echo 'CROSS_MAKECONF must select a cross build' >&2; exit 2; }
mk configure >"$work/configure.log" 2>&1
mk pre-build >>"$work/configure.log" 2>&1
wrksrc=$(mk show-var VARNAME=WRKSRC)
b2=$(mk show-var VARNAME=BJAM)
ver=$(mk show-var VARNAME=PYVERSSUFFIX)
suffix=$(echo "$ver" | tr -d .)
# Run the recipe's own b2 command line as a dry run.
dry() {
    mk BJAM="$b2 -n -a --debug-configuration" bjam-build >"$work/$1.log" 2>&1 || true
}
fail() { echo "FAIL: $*" >&2; exit 1; }

dry patched
grep -q "libboost_python$suffix\.so" "$work/patched.log" || fail "patched config does not build libboost_python$suffix"
grep -q "libboost_numpy$suffix\.so" "$work/patched.log" || fail "patched config does not build libboost_numpy$suffix"
grep -q 'numpy/_core/include' "$work/patched.log" || fail 'target NumPy include directory missing'
! grep -q 'No python installation configured' "$work/patched.log" || fail 'patched config left Python unconfigured'

cp "$wrksrc/user-config.jam" "$work/user-config.jam.patched"
printf 'using python : %s : /usr/pkg/bin/python%s : /usr/pkg/include/python%s ;\n' "$ver" "$ver" "$ver" >"$wrksrc/user-config.jam"
dry upstream
cp "$work/user-config.jam.patched" "$wrksrc/user-config.jam"
grep -q 'No python installation configured' "$work/upstream.log" || fail 'upstream config unexpectedly configured Python'
! grep -q "libboost_numpy$suffix\.so" "$work/upstream.log" || fail 'upstream config unexpectedly builds Boost.NumPy'
echo "PASS: cross user-config.jam selects Boost.Python and Boost.NumPy; upstream one does not"

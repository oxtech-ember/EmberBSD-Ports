#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). GNU libidn installs include/idna.h, so
# ada-idna must not. Apply this recipe's patches to the release archive,
# build and install it with CMake into a scratch prefix, and check that the
# installed headers match the PLIST, share no path with devel/libidn, and
# serve tests/consumer.cpp. Installs nothing outside NEW_OUTPUT.
# Usage: install-headers.sh PKGSRC DISTFILE NEW_OUTPUT
# PKGSRC is a complete tree that provides devel/libidn.
# Environment: CMAKE, CXX (C++20), PATCH (GNU patch), MAKE_PROGRAM.
set -eu
[ "$#" = 3 ] || { echo "Usage: $0 PKGSRC DISTFILE NEW_OUTPUT" >&2; exit 2; }
: "${CMAKE:?Set cmake}" "${CXX:?Set a C++20 compiler}" "${PATCH:?Set GNU patch}"
: "${MAKE_PROGRAM:?Set the CMake make program}"
pkgsrc=$1 dist=$2 out=$3
for path in "$@"; do
    case "$path" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2 ;; esac
done
recipe=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
mkdir "$out"
out=$(CDPATH= cd -- "$out" && pwd -P)
fail() { echo "FAIL: $*" >&2; exit 1; }
tar -xzf "$dist" -C "$out"
src=$out/idna-0.7.0
for p in "$recipe"/patches/patch-*; do
    (cd "$src" && "$PATCH" -p0 -s --no-backup-if-mismatch < "$p") ||
        fail "$(basename "$p") does not apply"
done
"$CMAKE" -S "$src" -B "$out/build" -DCMAKE_MAKE_PROGRAM="$MAKE_PROGRAM" \
    -DCMAKE_CXX_COMPILER="$CXX" -DCMAKE_INSTALL_PREFIX="$out/prefix" \
    -DBUILD_SHARED_LIBS=ON -DBUILD_TESTING=OFF -DADA_USE_SIMDUTF=OFF \
    > "$out/configure.log" 2>&1 || { tail -20 "$out/configure.log" >&2; fail configure; }
"$CMAKE" --build "$out/build" > "$out/build.log" 2>&1 ||
    { tail -20 "$out/build.log" >&2; fail build; }
"$CMAKE" --install "$out/build" > "$out/install.log" 2>&1 ||
    { tail -20 "$out/install.log" >&2; fail install; }
(cd "$out/prefix" && find include -type f | LC_ALL=C sort) > "$out/installed"
grep '^include/' "$recipe/PLIST" | LC_ALL=C sort > "$out/plist"
cmp -s "$out/installed" "$out/plist" ||
    { diff "$out/plist" "$out/installed" >&2; fail "installed headers differ from the PLIST"; }
[ -f "$pkgsrc/devel/libidn/PLIST" ] || fail "no devel/libidn PLIST in $pkgsrc"
grep '^include/' "$pkgsrc/devel/libidn/PLIST" | LC_ALL=C sort > "$out/libidn"
shared=$(LC_ALL=C comm -12 "$out/installed" "$out/libidn")
[ -z "$shared" ] || fail "headers shared with devel/libidn: $shared"
"$CXX" -std=c++20 -fsyntax-only -I"$out/prefix/include" "$recipe/tests/consumer.cpp" ||
    fail "tests/consumer.cpp does not compile against the installed headers"
echo "PASS: $(wc -l < "$out/installed" | tr -d ' ') ada-idna headers match the PLIST and avoid devel/libidn paths"

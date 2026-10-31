#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake grpc-latent-see-abs.sh PKGSRC MAKECONF
#
# grpc's NetBSD patch narrowed earliest_timestamp to int to match abs(int).
# With libc++, abs(int64_t) is the long overload, so std::min saw int and
# long and net/grpc stopped with "no matching function for call to 'min'".
# Patch the recipe and compile its earliest_timestamp update for the target.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
recipe=$1/net/grpc makeconf=$2
bm() { MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$recipe" MAKECONF="$makeconf" SKIP_DEPENDS=yes "$@"; }
src=$(bm -V '${WRKSRC}') cxx=$(bm -V '${TOOLDIR:U}/bin/${CXX}') sysroot=$(bm -V '${CROSS_DESTDIR:U}')
[ -n "$sysroot" ] || { cxx=$(bm -V '${CXX}'); }
tmp=$(mktemp -d)
trap 'bm clean >/dev/null 2>&1 || :; rm -rf "$tmp"' EXIT
bm clean >/dev/null 2>&1 || :
bm patch >/dev/null 2>&1 || { echo "FAIL: patch"; exit 1; }
# The "earliest_timestamp =" statement in Collect(), up to its semicolon.
stmt=$(awk '/earliest_timestamp =[ \t]*$/ { on = 1 } on { print; if (/;[ \t]*$/) exit }' \
	"$src/src/core/util/latent_see.cc")
case $stmt in *earliest_timestamp*) ;; *) echo "FAIL: statement not found"; exit 1 ;; esac
cat > "$tmp/t.cc" <<EOT
#include <algorithm>
#include <cstdint>
#include <cstdlib>
#include <type_traits>
struct Event { int64_t timestamp_end; };
int64_t update(int64_t earliest_timestamp, Event event) {
$stmt
  return earliest_timestamp;
}
EOT
"$cxx" ${sysroot:+--sysroot="$sysroot"} -std=c++17 -fsyntax-only "$tmp/t.cc" ||
	{ echo "FAIL: earliest_timestamp update does not compile"; exit 1; }
echo "PASS: grpc keeps earliest_timestamp in int64_t"

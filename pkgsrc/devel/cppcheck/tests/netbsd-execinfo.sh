#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake netbsd-execinfo.sh PKGSRC MAKECONF
#
# cli/stacktrace.cpp calls backtrace(3) when <execinfo.h> exists. NetBSD
# declares it there but provides it in libexecinfo, which cppcheck's CMake
# does not link, so test-stacktrace failed with "undefined symbol:
# backtrace". Link a backtrace() caller with the recipe's cross LDFLAGS.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 PKGSRC MAKECONF" >&2; exit 2; }
recipe=$1/devel/cppcheck makeconf=$2
bm() { MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$recipe" MAKECONF="$makeconf" "$@"; }
[ "$(bm -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] && [ "$(bm -V '${OPSYS}')" = NetBSD ] ||
	{ echo "$0: select a MAKECONF for a NetBSD cross build" >&2; exit 2; }
cxx=$(bm -V '${TOOLDIR}/bin/${_EMBER_CROSS_TRIPLET}-clang++')
ldflags=$(bm -V '${LDFLAGS}')
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
cat > "$tmp/t.cpp" <<'EOS'
#include <execinfo.h>
int main() { void *a[4]; int n = backtrace(a, 4); char **s = backtrace_symbols(a, n); return s == 0; }
EOS
# shellcheck disable=SC2086
if "$cxx" -o "$tmp/t" "$tmp/t.cpp" $ldflags >"$tmp/log" 2>&1; then
	echo "PASS: NetBSD links backtrace(3) from libexecinfo"
else
	cat "$tmp/log"; echo "FAIL: backtrace(3) does not link with the cross LDFLAGS"; exit 1
fi

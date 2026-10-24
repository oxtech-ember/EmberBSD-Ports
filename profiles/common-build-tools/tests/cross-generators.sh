#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), keep auxiliary generators on the build host.
set -eu
unset CC_FOR_BUILD CXX_FOR_BUILD
[ "$#" = 4 ] || { echo "Usage: $0 PKGSRC CROSS_MAKECONF NATIVE_MAKECONF NEW_WORK" >&2; exit 2; }
pkgsrc=$1 crossconf=$2 nativeconf=$3 work=$4
bmake=${BMAKE:-bmake}
mkdir "$work"
query() { "$bmake" -C "$pkgsrc/devel/binutils" MAKECONF="$crossconf" -v "$1"; }
depcomp=$(query _OVERRIDE_PATH.depcomp)
toolbase=$(query TOOLBASE)
platform=$(query MACHINE_PLATFORM)
[ "$depcomp" = "$toolbase/cross-$platform/share/libtool/build-aux/depcomp" ]
[ -x "$depcomp" ]
cat > "$work/generator.c" <<'C'
#include <stdio.h>
int main(void) { puts("generated on build host"); return 0; }
C
cat > "$work/generator.cc" <<'CXX'
#include <iostream>
int main() { std::cout << "C++ generated on build host\n"; }
CXX
cat > "$work/configure-probe.sh" <<'SH'
#!/bin/sh
set -eu
work=$1 depcomp=$2
: "${CC_FOR_BUILD:?Missing CC_FOR_BUILD in configure environment}"
: "${CXX_FOR_BUILD:?Missing CXX_FOR_BUILD in configure environment}"
# Standard pkgsrc compiler commands contain a path and optional arguments.
# Split words as upstream configure does; do not evaluate shell syntax.
set -f
case "$CC_FOR_BUILD:$CXX_FOR_BUILD" in /*:/*) ;; *) exit 1;; esac
depmode=none source="$work/generator.c" object="$work/generator.o" \
    "$depcomp" $CC_FOR_BUILD -c "$work/generator.c" -o "$work/generator.o"
$CC_FOR_BUILD "$work/generator.o" -o "$work/generator"
[ "$("$work/generator")" = 'generated on build host' ]
$CXX_FOR_BUILD "$work/generator.cc" -o "$work/generator-cxx"
[ "$("$work/generator-cxx")" = 'C++ generated on build host' ]
SH
cat > "$work/generator.mk" <<'MAKE'
.include "${.CURDIR}/Makefile"
.PHONY: ember-host-generator
ember-host-generator:
	${RUN} ${SETENV} ${CONFIGURE_ENV} ${SH} ${EMBER_PROBE_WORK:Q}/configure-probe.sh ${EMBER_PROBE_WORK:Q} ${_OVERRIDE_PATH.depcomp:Q}
MAKE
# Exercise the actual environment delivered to configure, not a separately
# queried compiler value that would conceal a missing CONFIGURE_ENV export.
"$bmake" -C "$pkgsrc/devel/binutils" -f "$work/generator.mk" \
    MAKECONF="$crossconf" EMBER_PROBE_WORK="$work" ember-host-generator
if "$bmake" -C "$pkgsrc/devel/binutils" -f "$work/generator.mk" \
    MAKECONF="$crossconf" EMBER_PROBE_WORK="$work" CONFIGURE_ENV= \
    ember-host-generator > "$work/missing-env.log" 2>&1; then
    echo 'Missing configure environment unexpectedly passed' >&2; exit 1
fi
grep -q 'Missing CC_FOR_BUILD in configure environment' "$work/missing-env.log"
native_depcomp=$("$bmake" -C "$pkgsrc/devel/binutils" MAKECONF="$nativeconf" -v _OVERRIDE_PATH.depcomp)
native_base=$("$bmake" -C "$pkgsrc/devel/binutils" MAKECONF="$nativeconf" -v TOOLBASE)
case "$native_depcomp" in
"$native_base/share/libtool/config/depcomp"|"$native_base/share/libtool/build-aux/depcomp") ;;
*) echo "Unexpected native depcomp: $native_depcomp" >&2; exit 1;;
esac
# The SDK-rendered include pins the native drivers; any override is refused.
for compiler in cc /nonexistent/ember-host-cc /usr/bin/cc; do
    if "$bmake" -C "$pkgsrc/devel/binutils" MAKECONF="$crossconf" \
        EMBERBSD_CROSS_BUILD_CC="$compiler" -v PKG_FAIL_REASON > "$work/invalid-cc.txt" 2>&1; then
        echo "Override $compiler unexpectedly accepted" >&2; exit 1
    fi
    grep -q 'EMBERBSD_CROSS_BUILD_CC differs from the qualified SDK tool' "$work/invalid-cc.txt"
done
echo 'PASS: cross/native auxiliary selection, real host generator and invalid host compiler guards'

#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), evaluate build and installed Perl in a cross recipe.
# A perl:run cross recipe with a staged target Perl must run the host Perl at
# build time (tools wrapper, TOOLS_PERL5, configure PERL) and name the target
# Perl only in installed scripts (PERL5, REPLACE_PERL).
# Usage: BMAKE=... cross-perl-tools.sh PKGSRC MAKECONF NEW_WORK [MAKE_ARG...]
# MAKECONF selects a cross sysroot that contains usr/pkg/bin/perl.
set -eu
[ "$#" -ge 3 ] || { echo "Usage: $0 PKGSRC MAKECONF NEW_WORK [MAKE_ARG...]" >&2; exit 2; }
pkgsrc=$1 makeconf=$2 work=$3
shift 3
: "${BMAKE:?Set the native BSD make command}"
for path in "$pkgsrc" "$makeconf" "$work"; do
    case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2 ;; esac
done
mkdir "$work"
query() {
    MAKECONF=$makeconf $BMAKE -C "$pkgsrc/devel/automake" "$@" REPLACE_PERL=bin/fixture \
        show-var VARNAME="$var" < /dev/null
}
for var in USE_CROSS_COMPILE CROSS_DESTDIR PREFIX TOOLS_PATH.perl TOOLS_PERL5 PERL5 \
    REPLACE.sys-Perl.new CONFIGURE_ENV; do
    query "$@" > "$work/$var" 2> "$work/$var.err" ||
        { cat "$work/$var.err" >&2; echo "FAIL: query $var" >&2; exit 1; }
done
value() { cat "$work/$1"; }
[ "$(value USE_CROSS_COMPILE)" = yes ] || { echo 'Select a cross MAKECONF.' >&2; exit 2; }
[ -f "$(value CROSS_DESTDIR)/usr/pkg/bin/perl" ] ||
    { echo 'Stage the target Perl package in the sysroot first.' >&2; exit 2; }
target=$(value PREFIX)/bin/perl
host=$(value TOOLS_PATH.perl)
case "$host" in /*) ;; *) echo "FAIL: build Perl is not absolute: $host" >&2; exit 1 ;; esac
[ "$host" != "$target" ] || { echo "FAIL: build steps run the target Perl $target" >&2; exit 1; }
[ -x "$host" ] || { echo "FAIL: build Perl $host does not execute here" >&2; exit 1; }
[ "$("$host" -e 'print $^O')" != netbsd ] || { echo 'FAIL: build Perl is not a host Perl' >&2; exit 1; }
[ "$(value TOOLS_PERL5)" = "$host" ] || { echo 'FAIL: TOOLS_PERL5 differs from the wrapper' >&2; exit 1; }
grep -q "PERL=$host\\( \\|\$\\)" "$work/CONFIGURE_ENV" ||
    { echo 'FAIL: configure PERL is not the build Perl' >&2; exit 1; }
[ "$(value PERL5)" = "$target" ] || { echo 'FAIL: PERL5 is not the target Perl' >&2; exit 1; }
[ "$(value REPLACE.sys-Perl.new)" = "$target" ] ||
    { echo 'FAIL: installed scripts do not name the target Perl' >&2; exit 1; }
echo "PASS: build steps use $host; installed scripts use $target"

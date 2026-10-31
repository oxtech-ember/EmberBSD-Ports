#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: devel-checklib-cross-execute.sh PKGSRC DISTFILE PERL NEW_WORK
#
# Devel::CheckLib runs the program it links to prove that a library works.
# In a cross build Makefile.PL gets the target Config through
# ExtUtils::MakeMaker::Config, the program is a target executable, and
# running it on the build machine failed ("cannot execute binary file"),
# so textproc/p5-XML-Parser reported that expat was missing. Apply the
# pkgsrc patches to DISTFILE, link a probe whose program exits 1, and
# require that a cross build context only links it while a native run
# still executes it and reports the wrong result.
set -eu
[ "$#" -eq 4 ] || { echo "Usage: $0 PKGSRC DISTFILE PERL NEW_WORK" >&2; exit 2; }
pkgsrc=$1 distfile=$2 perl=$3
unset EMBERBSD_PERL_BUILD_CONFIG
case "$4" in /*) ;; *) echo "$0: NEW_WORK must be absolute" >&2; exit 2;; esac
mkdir "$4"
work=$4
tar -xzf "$distfile" -C "$work"
src=$(echo "$work"/Devel-CheckLib-*)
for p in "$pkgsrc"/devel/p5-Devel-CheckLib/patches/patch-*; do
	[ -f "$p" ] && (cd "$src" && patch -s -p0 < "$p")
done
printf '{"osname":"netbsd"}\n' > "$work/target.json"
[ "$(EMBERBSD_PERL_BUILD_CONFIG=$work/target.json "$perl" -MExtUtils::MakeMaker::Config \
	-e 'print $Config{osname}')" = netbsd ] ||
	{ echo "$0: PERL must read EMBERBSD_PERL_BUILD_CONFIG in ExtUtils::MakeMaker::Config" >&2; exit 2; }
probe() {
	(cd "$work" && "$perl" -I"$src/lib" -MDevel::CheckLib -e \
		'print check_lib(lib => "m", header => "stdio.h", function => "return 1;") ? "linked" : "rejected"')
}
status=0
got=$(EMBERBSD_PERL_BUILD_CONFIG=$work/target.json probe)
[ "$got" = linked ] || { echo "FAIL: a cross build context ran the target probe ($got)"; status=1; }
got=$(probe)
[ "$got" = rejected ] || { echo "FAIL: a native run did not execute the probe ($got)"; status=1; }
[ "$status" -eq 0 ] || exit 1
echo "PASS: cross builds link Devel::CheckLib probes without running them"

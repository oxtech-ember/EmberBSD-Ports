#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
set -eu
[ "$#" = 1 ] || { echo "Usage: $0 NEW_WORK" >&2; exit 2; }
case "$1" in /*) ;; *) exit 2 ;; esac
source=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
mkdir "$1"
work=$(CDPATH= cd -- "$1" && pwd)
cp "$source/Makefile.PL" "$source/EmberProbe.pm" "$source/EmberProbe.xs" "$work/"
mkdir "$work/t"
cp "$source/t/native.t" "$work/t/"
PATH=/usr/pkg/bin:/usr/pkg/gcc16/bin:/usr/bin:/bin:/usr/sbin:/sbin; export PATH
unset PERL5LIB PERL5OPT PERL_CORE LD_LIBRARY_PATH
cd "$work"
/usr/pkg/bin/perl Makefile.PL > configure.log 2>&1
/usr/bin/make > build.log 2>&1
/usr/bin/make test > test.log 2>&1
ldd blib/arch/auto/EmberProbe/EmberProbe.so > ldd.txt
sha256 blib/arch/auto/EmberProbe/EmberProbe.so > outputs.sha256
cat test.log

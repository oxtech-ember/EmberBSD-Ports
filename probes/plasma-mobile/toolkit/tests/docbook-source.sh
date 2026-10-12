#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), verify the target DocBook Perl dependency.
set -eu
[ "$#" = 3 ] || { echo 'Usage: docbook-source.sh PKGSRC PACKAGE NEW_WORK' >&2; exit 2; }
prepared=$1 package=$2
: "${BMAKE:?Set native bmake}" "${MAKECONF:?Set the cross MAKECONF}"
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../../.." && pwd)
mkdir "$3"
work=$(CDPATH= cd -- "$3" && pwd)
mkdir "$work/pkgsrc"
git -C "$root/upstream/pkgsrc" archive HEAD textproc/docbook-xsl > "$work/recipe.tar"
tar -xf "$work/recipe.tar" -C "$work/pkgsrc"
patch -f -N -F 0 -p1 -d "$work/pkgsrc" < "$root/probes/plasma-mobile/toolkit/docbook-cross.patch" > "$work/patch.log"
cmp "$work/pkgsrc/textproc/docbook-xsl/Makefile" "$prepared/textproc/docbook-xsl/Makefile"
if patch -f -N -F 0 -p1 -d "$work/pkgsrc" < "$root/probes/plasma-mobile/toolkit/docbook-cross.patch" > "$work/repeated.log" 2>&1; then exit 1; fi
recipe=$prepared/textproc/docbook-xsl
"$BMAKE" -C "$recipe" -V '${PKG_FAIL_REASON}' > "$work/reasons.txt"
[ -z "$(cat "$work/reasons.txt")" ]
"$BMAKE" -C "$recipe" -V '${DEPENDS}' > "$work/depends.txt"
grep -q 'perl>=5.44.0' "$work/depends.txt"
"$BMAKE" -C "$recipe" USE_CROSS_COMPILE=no -V '${USE_TOOLS}' > "$work/native-tools.txt"
grep -q 'perl:run' "$work/native-tools.txt"
tar -xOf "$package" share/xsl/docbook/fo/pdf2index > "$work/pdf2index"
head -1 "$work/pdf2index" | grep -E '^#!/usr/pkg/bin/perl([[:space:]]|$)'
tar -xOf "$package" +CONTENTS > "$work/contents.txt"
grep -q '@pkgdep perl>=5.44.0' "$work/contents.txt"
shasum -a 256 "$package" > "$work/package.sha256"
echo 'PASS: zero-fuzz recipe, repeated patch rejection, native Perl preserved, target dependency and installed shebang'

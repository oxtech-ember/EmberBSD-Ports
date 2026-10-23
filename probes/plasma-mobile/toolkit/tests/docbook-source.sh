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
# The DocBook XSL recipe is a canonical pkgsrc/ recipe.
[ "$(grep -cxF textproc/docbook-xsl "$root/pkgsrc/replaces")" = 1 ]
diff -r "$root/pkgsrc/textproc/docbook-xsl" "$prepared/textproc/docbook-xsl"
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
echo 'PASS: exact canonical recipe, native Perl preserved, target dependency and installed shebang'

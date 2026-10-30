#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). fo/pdf2index is installed for the target.
# In cross mode, run the recipe's real REPLACE_PERL edit: the script must name
# the target Perl, and lang/perl5 must be a run-time dependency so the pkgsrc
# interpreter check finds it in the sysroot. Then run the real post-install
# catalog rewrite: it must run the build host Perl through the tools wrapper,
# not the target Perl path. Builds nothing.
# Usage: cross-perl.sh PKGSRC MAKECONF NEW_OUTPUT
set -eu
[ "$#" = 3 ] || { echo "Usage: $0 PKGSRC MAKECONF NEW_OUTPUT" >&2; exit 2; }
: "${BMAKE:?Set native bmake}"
pkgsrc=$1 conf=$2 out=$3
for path in "$@"; do
    case "$path" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2 ;; esac
done
mkdir "$out"
out=$(CDPATH= cd -- "$out" && pwd -P)
fail() { echo "FAIL: $*" >&2; exit 1; }
run() {
    "$BMAKE" -C "$pkgsrc/textproc/docbook-xsl-ns" MAKECONF="$conf" \
        USE_CROSS_COMPILE=yes WRKDIR="$out/work" WRKSRC="$out/src" \
        DESTDIR="$out/stage" "$@"
}
prefix=$(run -V '${PREFIX}')
xsldir=$(run -V '${XSLDIR}')
case " $(run -V '${DEPENDS}') " in
*:../../lang/perl5" "*) ;;
*) fail "lang/perl5 is not a run-time dependency" ;;
esac
mkdir -p "$out/src/fo" "$out/stage$xsldir"
# The upstream 1.79.2 first line.
printf '%s\nprint "ok\\n";\n' '#!/usr/bin/perl -- # -*- Perl -*-' > "$out/src/fo/pdf2index"
chmod 755 "$out/src/fo/pdf2index"
run replace-interpreter > "$out/replace.log" 2>&1 ||
    { cat "$out/replace.log" >&2; fail "replace-interpreter failed"; }
first=$(sed -n 1p "$out/src/fo/pdf2index")
[ "$first" = "#!$prefix/bin/perl -- # -*- Perl -*-" ] ||
    fail "pdf2index names $first, not the target $prefix/bin/perl"
# post-install edits the staged catalog with Perl on the build host.
printf '<rewriteURI rewritePrefix="./"/>\n' > "$out/stage$xsldir/catalog.xml"
run override-tools > "$out/tools.log" 2>&1 ||
    { cat "$out/tools.log" >&2; fail "tools wrapper setup failed"; }
run post-install > "$out/post-install.log" 2>&1 ||
    { cat "$out/post-install.log" >&2; fail "post-install did not run a host Perl"; }
grep -F "rewritePrefix=\"$xsldir/\"" "$out/stage$xsldir/catalog.xml" > /dev/null ||
    fail "post-install did not rewrite the catalog"
echo "PASS: pdf2index names $prefix/bin/perl; post-install runs the host Perl"

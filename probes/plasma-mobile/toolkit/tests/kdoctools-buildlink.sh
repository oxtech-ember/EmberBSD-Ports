#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Generate a KService manual page with the
# relocatable KDocTools stylesheet from the consumer's buildlink directory.
# Install the KService dependencies into the cross sysroot first.
set -eu
[ "$#" = 2 ] || { echo 'Usage: kdoctools-buildlink.sh PKGSRC NEW_WORK' >&2; exit 2; }
: "${BMAKE:?Set native bmake}" "${MAKECONF:?Set the cross MAKECONF}"
recipe=$1/devel/kf6-kservice
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
run() { "$BMAKE" -C "$recipe" MAKECONF="$MAKECONF" WRKOBJDIR="$work/obj" "$@"; }
# The consumer gets DocBook XSL as a build dependency only.
run -V '${BUILD_DEPENDS}' | tr ' ' '\n' > "$work/build-depends.txt"
grep -qx 'docbook-xsl>=1.79.2nb8:../../textproc/docbook-xsl' "$work/build-depends.txt"
if run -V '${DEPENDS}' | grep -q docbook-xsl; then exit 1; fi
# The KDocTools filter keeps the pkgsrc default terms and adds customization.
default=$(sed -n '/^BUILDLINK_CONTENTS_FILTER\.\${_pkg_}?=/{n;p;}' \
    "$1/mk/buildlink3/bsd.buildlink3.mk" | sed "s/^[^']*'//; s/'.*//" | sed 's/\$\$/$/g')
filter=$(run -V '${BUILDLINK_CONTENTS_FILTER.kf6-kdoctools}' | sed "s/^[^']*'//; s/'.*//")
[ -n "$default" ]
[ "$filter" = "${default%)}|^share/kf6/kdoctools/customization/)" ]
host=$(run -V '${TOOLBASE}')
run wrapper > "$work/wrapper.log" 2>&1 || { tail -20 "$work/wrapper.log" >&2; exit 1; }
wrkdir=$(run -V '${WRKDIR}')
wrksrc=$(run -V '${WRKSRC}')
style=$wrkdir/.buildlink/share/kf6/kdoctools/customization/kde-include-man.xsl
[ -L "$style" ]
for page in docs/kbuildsycoca6 po/de/docs/kbuildsycoca6; do
	out=$work/$(echo "$page" | tr / _)
	mkdir "$out"
	(cd "$out" && "$host/bin/meinproc6" --stylesheet "$style" --check \
	    "$wrksrc/$page/man-kbuildsycoca6.8.docbook") > "$out.log" 2>&1 ||
	    { cat "$out.log" >&2; exit 1; }
	if grep -v '^Note: Writing kbuildsycoca6\.8$' "$out.log"; then exit 1; fi
	grep -q '^\.TH .*KBUILDSYCOCA6.* "8" ' "$out/kbuildsycoca6.8"
done
echo 'PASS: English and translated manual pages use the buildlinked DocBook XSL tree'

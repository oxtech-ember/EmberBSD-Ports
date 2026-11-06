#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
# The selected host msgfmt keeps ITS rules beside its prefix.
# GNU msgfmt searches $GETTEXTDATADIR/its and then
# $GETTEXTDATADIR$PACKAGE_SUFFIX/its. Relocation must use the selected
# executable directory, including when that executable is a symlink to a
# producer copy, and must leave the version suffix to the tool.
# Usage: gettext-datadir.sh NEW_OUTPUT
set -eu
[ "$#" = 1 ] || { echo 'Usage: gettext-datadir.sh NEW_OUTPUT' >&2; exit 2; }
out=$1
case "$out" in /*) ;; *) echo 'NEW_OUTPUT must be absolute' >&2; exit 2 ;; esac
[ ! -e "$out" ] || exit 2
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd -P)
mkdir -p "$out"
fail() { echo "FAIL: $*" >&2; exit 1; }
selected_datadir() {
    bindir=$(CDPATH= cd -- "$(dirname -- "$1")" && pwd -P)
    printf '%s/share/gettext\n' "$(dirname -- "$bindir")"
}
# Mirror gettext-tools src/search-path.c: unversioned directory, then the
# compiled PACKAGE_SUFFIX directory. Locating rules live in the its/ child.
its_has_metainfo() {
    datadir=$1 suffix=$2
    [ -f "$datadir/its/metainfo.loc" ] || [ -f "$datadir$suffix/its/metainfo.loc" ]
}
producer=$out/producer
selected=$out/selected
mkdir -p "$producer/bin" "$producer/share/gettext/its" \
    "$selected/bin" "$selected/share/gettext/its" "$selected/share/gettext-1.0/its"
printf '#!/bin/sh\nexit 0\n' > "$producer/bin/msgfmt"
chmod +x "$producer/bin/msgfmt"
ln -s "$producer/bin/msgfmt" "$selected/bin/msgfmt"
printf '<locatingRule pattern="*.metainfo.xml"/>\n' > "$selected/share/gettext-1.0/its/metainfo.loc"
printf '<locatingRule pattern="*.gschema.xml"/>\n' > "$selected/share/gettext/its/gschema.loc"
data=$(selected_datadir "$selected/bin/msgfmt")
[ "$data" = "$selected/share/gettext" ] || fail "selected prefix became $data"
case "$data" in
    "$producer"/*) fail 'followed the producer symlink' ;;
    */gettext-1.0) fail 'version suffix was hardcoded' ;;
esac
its_has_metainfo "$producer/share/gettext" -1.0 && fail 'producer tree should not satisfy metainfo'
its_has_metainfo "$data" -1.0 || fail 'versioned ITS rules were not reached from the unversioned directory'
its_has_metainfo "$selected/share/gettext" '' && fail 'unversioned its/ alone must not be treated as metainfo'
explicit=$out/explicit/share/gettext
[ "$explicit" != "$data" ] || fail 'fixture collision'
# An explicit GETTEXTDATADIR is the caller's value.
GETTEXTDATADIR=$explicit
if [ -n "${GETTEXTDATADIR:-}" ]; then
    kept=$GETTEXTDATADIR
else
    kept=$data
fi
[ "$kept" = "$explicit" ] || fail 'explicit data directory was replaced'
unset GETTEXTDATADIR
patch=$ports/profiles/common-build-tools/patches/pkgsrc-gettext-datadir.patch
[ -f "$patch" ] || fail 'host data-directory patch is missing'
grep -q 'cd "$$(dirname ${EMBERBSD_BUILD_MSGFMT:Q})" && pwd -P' "$patch" ||
    fail 'patch does not resolve the selected executable directory'
grep -q 'GETTEXTDATADIR= ${_EMBERBSD_MSGFMT_BINDIR:H}/share/gettext' "$patch" ||
    fail 'patch does not keep the unversioned data directory'
grep -q 'devel/gettext-tools' "$patch" || fail 'patch does not skip the gettext-tools build'
grep -q -- '--enable-relocatable' \
    "$ports/profiles/common-build-tools/patches/gettext-external-recipe.patch" ||
    fail 'gettext-tools is not built relocatable'
grep -q 'PKGREVISION=	8' \
    "$ports/profiles/common-build-tools/patches/pkgsrc-gettext-external-tree-sitter.patch" ||
    fail 'gettext-tools revision was not advanced'
grep -q 'PKGREVISION= 9' \
    "$ports/profiles/common-build-tools/patches/pkgsrc-gettext-external-tree-sitter.patch" ||
    fail 'Darwin gettext-tools revision was not advanced'
echo 'PASS: selected host prefix supplies versioned gettext ITS data'

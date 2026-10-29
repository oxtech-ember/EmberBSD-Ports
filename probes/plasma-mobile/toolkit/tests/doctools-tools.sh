#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), native DocBook execution and cross input checks.
set -eu
[ "$#" = 4 ] || { echo 'Usage: doctools-tools.sh PKGSRC TOOLBASE KDOCTOOLS_SOURCE NEW_WORK' >&2; exit 2; }
pkgsrc=$1 host=$2 source=$3 work=$4
: "${BMAKE:?Set native bmake}" "${MAKECONF:?Set the cross-package MAKECONF}"
mkdir "$work"
recipe=$pkgsrc/devel/kf6-kdoctools
imports=lib/cmake/KF6DocTools
"$BMAKE" -C "$recipe" "TOOLBASE=$host" emberbsd-native-doctools-check > "$work/valid.log" 2>&1
for bad in old missing-tool missing-imports; do
    mkdir -p "$work/$bad/bin" "$work/$bad/$imports"
    for program in meinproc6 checkXML6 docbookl10nhelper; do
        ln -s "$host/bin/$program" "$work/$bad/bin/$program"
    done
    for import in "$host/$imports"/*; do
        ln -s "$import" "$work/$bad/$imports/${import##*/}"
    done
done
rm "$work/old/$imports/KF6DocToolsConfigVersion.cmake"
sed 's/PACKAGE_VERSION "6\.31\.0"/PACKAGE_VERSION "6.30.0"/' \
    "$host/$imports/KF6DocToolsConfigVersion.cmake" > "$work/old/$imports/KF6DocToolsConfigVersion.cmake"
rm "$work/missing-tool/bin/checkXML6"
rm "$work/missing-imports/$imports/KF6DocToolsToolsTargets.cmake"
for bad in old missing-tool missing-imports absent; do
    if "$BMAKE" -C "$recipe" "TOOLBASE=$work/$bad" emberbsd-native-doctools-check > "$work/$bad.log" 2>&1; then
        echo "Invalid native DocTools accepted: $bad" >&2; exit 1
    fi
    grep -q 'Matching native KDocTools 6.31 generators are required' "$work/$bad.log"
done
for consumer in x11/kf6-kconfigwidgets devel/kf6-kservice security/kf6-kwallet; do
    name=${consumer##*/}
    "$BMAKE" -C "$pkgsrc/$consumer" -V '${TOOL_DEPENDS}' | tr -s ' ' '\n' > "$work/$name-tools.txt"
    grep -q '^kf6-kdoctools-generators-6\.31\.0' "$work/$name-tools.txt"
    if grep -q '^kf6-kdoctools[>-][0-9]' "$work/$name-tools.txt"; then exit 1; fi
    "$BMAKE" -C "$pkgsrc/$consumer" -V '${BUILD_DEPENDS}' > "$work/$name-build.txt"
    grep -q 'kf6-kdoctools>=6.31.0' "$work/$name-build.txt"
done
# Use upstream's original licensed fixture without copying it into this repo.
cp "$source/tests/create-from-current-dir-test/docs/kioslave/data/index.docbook" "$work/index.docbook"
shasum -a 256 "$work/index.docbook" > "$work/source.sha256"
PATH="$host/bin:$PATH"
export PATH
cd "$work"
checkXML6 index.docbook > valid-xml.log 2>&1
meinproc6 --check --output good.html index.docbook > valid-html.log 2>&1
grep -q 'Data URLs' good.html
# Well-formed XML with an invalid DocBook element must fail DTD validation.
sed 's@</article>@<not-docbook/></article>@' index.docbook > invalid.docbook
if checkXML6 invalid.docbook > invalid-xml.log 2>&1; then
    echo 'checkXML6 accepted an invalid DocBook element' >&2; exit 1
fi
if meinproc6 --check --output bad.html invalid.docbook > invalid-html.log 2>&1; then
    echo 'meinproc6 accepted an invalid DocBook element' >&2; exit 1
fi
grep -q 'validity error' invalid-xml.log
grep -q 'validity error' invalid-html.log
echo 'PASS: matching native tools, missing/old tool rejection, cross dependency classes, actual HTML generation and invalid DocBook failure'

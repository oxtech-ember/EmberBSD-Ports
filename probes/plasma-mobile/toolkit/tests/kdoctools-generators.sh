#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Cross KDocTools consumers get the native
# generators from a Ports TOOL_DEPENDS package, never from a configured prefix,
# so a bulk fetch or parse needs no build-host setting.
set -eu
[ "$#" = 3 ] || { echo 'Usage: kdoctools-generators.sh PKGSRC CROSS_MAKECONF NEW_WORK' >&2; exit 2; }
pkgsrc=$1 cross=$2 work=$3
: "${BMAKE:=bmake}"
mkdir "$work"
query() { # MAKECONF PKGPATH ARGS...
    config=$1 path=$2; shift 2
    MAKECONF="$config" "$BMAKE" -C "$pkgsrc/$path" _MAKEVARS_MK=defined _PKGSRC_BARRIER=yes "$@"
}
generators='kf6-kdoctools-generators-6.31.0{,nb[0-9]*}:../../devel/kf6-kdoctools-generators'
toolbase=$(query "$cross" devel/kf6-kdoctools -V '${TOOLBASE}')
[ -n "$toolbase" ]
# The target package and consumers that use KDocTools directly or through
# its buildlink file parse without a host setting and require the generators.
for path in devel/kf6-kdoctools devel/kf6-kpackage devel/kf6-kservice \
    x11/kf6-kconfigwidgets graphics/kf6-prison; do
    name=${path##*/}
    query "$cross" "$path" -V '${USE_CROSS_COMPILE:tl}' -V '${PKG_FAIL_REASON}' \
        -V '${TOOL_DEPENDS}' -V '${CMAKE_CONFIGURE_ARGS}' > "$work/$name.txt"
    [ "$(sed -n 1p "$work/$name.txt")" = yes ]
    if sed -n 2p "$work/$name.txt" | grep -q .; then
        echo "$path cannot be fetched or built: $(sed -n 2p "$work/$name.txt")" >&2; exit 1
    fi
    sed -n 3p "$work/$name.txt" | tr -s ' ' '\n' | grep -Fqx "$generators" ||
        { echo "$path does not depend on the native generators" >&2; exit 1; }
    sed -n 4p "$work/$name.txt" | tr -s ' ' '\n' > "$work/$name-cmake.txt"
    for arg in "-DKDOCTOOLS_TARGETSFILE=$toolbase/lib/cmake/KF6DocTools/KF6DocToolsToolsTargets.cmake" \
        "-DMEINPROC6_EXECUTABLE=$toolbase/bin/meinproc6" "-DCHECKXML6_EXECUTABLE=$toolbase/bin/checkXML6" \
        "-DDOCBOOKL10NHELPER_EXECUTABLE=$toolbase/bin/docbookl10nhelper"; do
        grep -Fqx -- "$arg" "$work/$name-cmake.txt"
    done
    if grep -q DOCTOOLS_HOST "$work/$name.txt"; then exit 1; fi
done
# The former prefix variable no longer selects anything.
query "$cross" devel/kf6-kservice EMBERBSD_KF6_DOCTOOLS_HOST=/nonexistent-ember-generator \
    -V '${PKG_FAIL_REASON}' -V '${CMAKE_CONFIGURE_ARGS}' > "$work/legacy.txt"
if grep -q nonexistent-ember-generator "$work/legacy.txt"; then exit 1; fi
query "$cross" devel/kf6-kdoctools -n emberbsd-native-doctools-check > "$work/check-plan.txt"
grep -Fq "$toolbase/lib/cmake/KF6DocTools" "$work/check-plan.txt"
grep -Fq 'PACKAGE_VERSION "6.31.0"' "$work/check-plan.txt"
# A TOOL_DEPENDS recursion builds the generators natively from the same
# release, and the package refuses cross builds.
query "$cross" devel/kf6-kdoctools-generators USE_CROSS_COMPILE=no -V '${USE_CROSS_COMPILE:Uno:tl}' -V '${PKG_FAIL_REASON}' \
    -V '${PKGNAME}' -V '${DISTFILES}' -V '${CMAKE_CONFIGURE_ARGS}' -V '${DEPENDS}' > "$work/native.txt"
[ "$(sed -n 1p "$work/native.txt")" = no ]
# The generators add no failure of their own to a native CMake build: compare
# with their native CMake dependency in the same configuration.
query "$cross" archivers/kf6-karchive USE_CROSS_COMPILE=no -V '${PKG_FAIL_REASON}' > "$work/native-reference.txt"
sed -n 2p "$work/native.txt" | cmp -s - "$work/native-reference.txt" ||
    { echo "The native generators cannot be built: $(sed -n 2p "$work/native.txt")" >&2; exit 1; }
[ "$(sed -n 3p "$work/native.txt")" = kf6-kdoctools-generators-6.31.0 ]
[ "$(sed -n 4p "$work/native.txt")" = "$(query "$cross" devel/kf6-kdoctools -V '${DISTFILES}')" ]
sed -n 5p "$work/native.txt" | grep -q -- '-DINSTALL_INTERNAL_TOOLS=ON'
sed -n 6p "$work/native.txt" | grep -q docbook-xsl
query "$cross" devel/kf6-kdoctools-generators -V '${PKG_FAIL_REASON}' > "$work/cross-generators.txt"
grep -q 'build-host tool' "$work/cross-generators.txt"
echo 'PASS: KDocTools cross consumers use the native Ports generators and need no host setting'

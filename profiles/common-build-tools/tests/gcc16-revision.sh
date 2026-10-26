#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted real pkgsrc repaired-compiler metadata check.
set -eu
[ "$#" = 4 ] || { echo 'Usage: gcc16-revision.sh EXPORTED_PKGSRC MAKE_WRAPPER PKG_ADMIN NEW_OUTPUT' >&2; exit 2; }
tree=$(CDPATH= cd -- "$1" && pwd)
make=$2
admin=$3
output=$4
[ ! -e "$output" ] && [ ! -L "$output" ] || exit 2
mkdir "$output"
printf 'EMBERBSD_HOST_COMPILER_FAMILY=gcc\n.include "%s/EMBERBSD-COMMON-TOOLS-MK.CONF"\n' "$tree" > "$output/mk.conf"
for recipe in devel/zlib textproc/icu; do
    name=${recipe##*/}
    MAKECONF="$output/mk.conf" "$make" -C "$tree/$recipe" \
        -V 'compiler=${_GCC_PKGBASE}' -V 'floor=${_GCC_REQD}' \
        -V 'runtime=${USE_PKGSRC_GCC_RUNTIME:tl}' \
        -V 'method=${BUILDLINK_DEPMETHOD.gcc16}' \
        -V 'gccdeps=${BUILDLINK_API_DEPENDS.gcc16}' \
        -V 'deps=${DEPENDS} ${BUILD_DEPENDS} ${TOOL_DEPENDS}' \
        -V 'fail=${PKG_FAIL_REASON}' > "$output/$name.log" 2>&1
    grep -qx 'compiler=gcc16' "$output/$name.log"
    grep -qx 'floor=16.2' "$output/$name.log"
    grep -qx 'runtime=no' "$output/$name.log"
    grep -qx 'method=full' "$output/$name.log"
    grep '^deps=.*gcc16>=16.2.0nb1:../../lang/gcc16' "$output/$name.log" >/dev/null
    ! grep -E 'gcc16-libs|warning:|no system rules|stopped making' "$output/$name.log"
    # Existing explicit host metadata limitations remain visible. No build runs.
    awk '/^fail=/ {
        text=$0
        while (match(text, /"[^"]*"/)) {
            reason=substr(text, RSTART+1, RLENGTH-2)
            text=substr(text, RSTART+RLENGTH)
            if (reason ~ /^[^ ]+ requires a working dlopen\(\)\.$/ ||
                reason ~ /^License conditions for [^ ]+ could not be evaluated$/) continue
            print reason > "/dev/stderr"; failed=1
        }
    } END { exit failed+0 }' "$output/$name.log"
done
if "$admin" pmatch 'gcc16>=16.2.0nb1' gcc16-16.2.0; then
    echo 'Unrepaired package unexpectedly matched.' >&2; exit 1
fi
for version in gcc16-16.2.0nb1 gcc16-16.2.0nb2; do
    "$admin" pmatch 'gcc16>=16.2.0nb1' "$version"
done
echo 'PASS: real C/C++ pkgsrc dependency requires nb1; GCC_REQD16.2/full/no-libs retained; package matcher rejects baseline and accepts nb1+'

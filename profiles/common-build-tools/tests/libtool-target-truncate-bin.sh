#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check that the target libtool names the
# target dd: configure records the dd it found on the build-host PATH.
set -eu
[ "$#" -eq 4 ] || {
    echo "Usage: $0 PKGSRC MAKECONF CLANG_CONFIGURED_LIBTOOL NEW_OUTPUT" >&2
    exit 2
}
: "${BMAKE:?Set the native bmake executable}"
pkgsrc=$1 conf=$2 configured=$3 out=$4
for path in "$@"; do
    case "$path" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2 ;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) echo 'Use paths without shell metacharacters' >&2; exit 2 ;; esac
done
mkdir "$out"
fail() { echo "FAIL: $*" >&2; exit 1; }
recipe() {
    "$BMAKE" -C "$pkgsrc/devel/libtool-base" MAKECONF="$conf" \
        EMBERBSD_CROSS_COMPILER_FAMILY=clang WRKOBJDIR="$out/work" "$@"
}
recipe -V 'PREFIX=${PREFIX}' -V 'HOST=${EMBERBSD_CROSS_HOST_PREFIX}' > "$out/metadata.log"
prefix=$(sed -n 's/^PREFIX=//p' "$out/metadata.log")
host=$(sed -n 's/^HOST=//p' "$out/metadata.log")
[ -n "$prefix" ] && [ -n "$host" ] || fail 'not a cross build with a host prefix'
grep -q '^lt_truncate_bin=' "$configured" || fail 'fixture has no lt_truncate_bin'
# The dd that configure finds first on the build-host PATH (host GNU tools).
mkdir -p "$out/src" "$out/wrk" "$out/destdir$prefix/bin"
sed "s|^lt_truncate_bin=.*|lt_truncate_bin=\"$host/gnu/bin/dd bs=4096 count=1\"|" \
    "$configured" > "$out/src/shlibtool"
for f in libtool libtoolize; do cp "$out/src/shlibtool" "$out/destdir$prefix/bin/$f"; done
recipe DESTDIR="$out/destdir" WRKSRC="$out/src" WRKDIR="$out/wrk" \
    ember-target-libtool > "$out/convert.log" 2>&1 ||
    { cat "$out/convert.log" >&2; fail 'conversion rejected the build-host dd'; }
for f in libtool libtoolize shlibtool; do
    grep -qx 'lt_truncate_bin="/bin/dd bs=4096 count=1"' "$out/destdir$prefix/bin/$f" ||
        fail "$f does not truncate with the target /bin/dd"
done
echo 'PASS: the target libtool truncates with /bin/dd'

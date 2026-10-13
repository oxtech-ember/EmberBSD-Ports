#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check cross shlibtool's configured dispatcher.
set -eu
[ "$#" -eq 5 ] || {
    echo "Usage: $0 PKGSRC MAKECONF CROSS_RECIPE HOST_PREFIX NEW_OUTPUT" >&2
    exit 2
}
: "${BMAKE:?Set the native bmake executable}"
pkgsrc=$1 conf=$2 recipe=$3 host_prefix=$4 out=$5
for path in "$@" "$BMAKE"; do
    case "$path" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2 ;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) echo 'Use paths without shell metacharacters' >&2; exit 2 ;; esac
done
mkdir "$out"
prefix=$out/prefix
mkdir -p "$prefix/bin" "$out/native" "$out/cross"
field() { sed -n "s/^$1=//p" "$2"; }
fail() { echo "FAIL: $*" >&2; exit 1; }
native_make() {
    "$BMAKE" -C "$pkgsrc/devel/libtool-base" MAKECONF="$conf" \
        USE_CROSS_COMPILE=no PREFIX="$prefix" \
        PKG_TOOLS_BIN="$host_prefix/sbin" WRKOBJDIR="$out/work" WRKSRC="$out/native" DESTDIR= MAKE_JOBS=2 "$@"
}
cross_make() {
    "$BMAKE" -C "$pkgsrc/cross/cross-libtool-base" -f "$recipe" MAKECONF="$conf" \
        USE_CROSS_COMPILE=no TARGET_MACHINE_ARCH=aarch64 TARGET_OPSYS=NetBSD \
        TARGET_OS_VERSION=11.0 TARGET_OPSYS_VERSION=110000 TARGET_OBJECT_FMT=ELF \
        TARGET_LOWER_OPSYS=netbsd PREFIX="$prefix" \
        PKG_TOOLS_BIN="$host_prefix/sbin" WRKOBJDIR="$out/work" WRKSRC="$out/cross" DESTDIR= MAKE_JOBS=2 "$@"
}
for mode in native cross; do
    "${mode}_make" -V 'FAIL=${PKG_FAIL_REASON}' -V 'PKGNAME=${PKGNAME}' \
        -V 'PREFIX=${PREFIX}' -V 'CONFIGURE_PREFIX=${GNU_CONFIGURE_PREFIX}' \
        -V 'MACHINE_PLATFORM=${MACHINE_PLATFORM}' -V 'PKG_DBDIR=${PKG_DBDIR}' \
        > "$out/$mode-metadata.log"
    [ -z "$(field FAIL "$out/$mode-metadata.log")" ] || fail "$mode metadata rejected"
done
platform=$(field MACHINE_PLATFORM "$out/cross-metadata.log")
[ "$platform" = NetBSD-11.0-aarch64 ] || fail 'unexpected cross platform'
[ "$(field CONFIGURE_PREFIX "$out/cross-metadata.log")" = "$prefix/cross-$platform" ] || fail 'unexpected cross prefix'
cp "$host_prefix/bin/libtool" "$out/native/libtool"
cp "$host_prefix/cross-$platform/bin/libtool" "$out/cross/libtool"
# Run the recipes' real generator and staged-install targets, without a build
# or package database mutation. Both dispatchers remain private to this test.
for mode in native cross; do
    "${mode}_make" post-build > "$out/$mode-build.log" 2>&1
    sh -n "$out/$mode/shlibtool"
done
mkdir -p "$prefix/cross-$platform/bin"
cp "$out/native/libtool" "$prefix/bin/libtool"
cp "$out/cross/libtool" "$prefix/cross-$platform/bin/libtool"
for mode in native cross; do
    "${mode}_make" post-install > "$out/$mode-install.log" 2>&1
done
"$prefix/bin/libtool" --tag=disable-static --config > "$out/native-direct.log"
"$prefix/bin/shlibtool" --config > "$out/native-dispatch.log"
cmp "$out/native-direct.log" "$out/native-dispatch.log"
"$prefix/cross-$platform/bin/libtool" --tag=disable-static --config > "$out/cross-direct.log"
"$prefix/cross-$platform/bin/shlibtool" --config > "$out/cross-dispatch.log"
cmp "$out/cross-direct.log" "$out/cross-dispatch.log" || fail 'cross shlibtool chose another libtool'
grep -qx 'host=aarch64--netbsd' "$out/cross-dispatch.log" || fail 'target tuple lost'
grep -qx 'host_os=netbsd' "$out/cross-dispatch.log" || fail 'target OS lost'
"$prefix/cross-$platform/bin/shlibtool" --features > "$out/cross-features.log"
grep -qx 'host: aarch64--netbsd' "$out/cross-features.log" || fail 'feature query changed target'
grep -qx 'enable shared libraries' "$out/cross-features.log" || fail 'shared libraries disabled'
grep -qx 'disable static libraries' "$out/cross-features.log" || fail 'shared-only tag lost'
# Recreate the original wrong-prefix dispatcher. It must select the host
# configuration, which differs from the cross configuration on a cross host.
sed "s|$prefix/cross-$platform/bin/libtool|$prefix/bin/libtool|" \
    "$prefix/cross-$platform/bin/shlibtool" > "$out/wrong-shlibtool"
chmod +x "$out/wrong-shlibtool"
"$out/wrong-shlibtool" --config > "$out/negative.log"
if cmp -s "$out/cross-direct.log" "$out/negative.log"; then
    fail 'wrong-prefix dispatcher was not detected'
fi
cmp "$out/native-direct.log" "$out/negative.log"
echo 'PASS: native and cross recipe generation/install, target dispatch and shared-only tag'
echo 'PASS: original host-prefix dispatch is rejected'
echo 'No source was compiled. No package database or shared prefix was changed.'

#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); check maintained macros against shipped output.
# The archive's generated files come from Automake 1.18.1, the Ports one is
# newer. The shipped configure deltas are therefore checked as a difference:
# regenerating the unchanged and the maintained trees with the same tools
# must change exactly the lines that the shipped deltas change.
set -eu
[ "$#" = 3 ] || { echo "Usage: $0 EXPORTED_PKGSRC VERIFIED_DISTFILES NEW_WORK" >&2; exit 2; }
pkgsrc=$1 distfiles=$2 work=$3
for path do
    case "$path" in /*) ;; *) exit 2 ;; esac
    case "$path" in *[!a-zA-Z0-9_./-]*) exit 2 ;; esac
done
[ ! -e "$work" ] && [ ! -L "$work" ] || exit 2
[ "$(autoconf --version | sed -n '1s/.* //p')" = 2.73 ]
[ "$(automake --version | sed -n '1s/.* //p')" = 1.19 ]
archive=$distfiles/libtool-2.6.2.tar.gz
[ "$(shasum -a 256 "$archive" | awk '{print $1}')" = 24adb3aa9ae035c70faba344af57d73215eb89281045af6c7ccd307751f8b0bf ]
mkdir -p "$work/original" "$work/packaged" "$work/unchanged" "$work/maintained"
recipe=$pkgsrc/devel/libtool
: "${DIGEST:?Set DIGEST to pkgsrc host digest}"
export DIGEST
(cd "$distfiles" && awk -f "$pkgsrc/mk/checksum/checksum.awk" -- "$recipe/distinfo" libtool-2.6.2.tar.gz)
awk -f "$pkgsrc/mk/checksum/checksum.awk" -- -p "$recipe/distinfo" "$recipe"/patches/patch-*
for dir in original packaged unchanged maintained; do
    tar -xf "$archive" --strip-components=1 -C "$work/$dir"
done
for delta in "$recipe"/patches/patch-*; do
    patch -f -N -F 0 -p0 -d "$work/packaged" < "$delta"
done
for delta in "$recipe"/patches/manual-*; do
    patch -f -N -F 0 -p0 -d "$work/maintained" < "$delta"
done
mkdir "$work/repeated"
cp "$work/packaged/configure" "$work/repeated/configure"
if patch -f -N -F 0 -p0 -d "$work/repeated" < "$recipe/patches/patch-configure" > "$work/repeated.log" 2>&1; then
    echo 'Repeated generated patch unexpectedly accepted' >&2; exit 1
fi
for dir in unchanged maintained; do
    (cd "$work/$dir" && aclocal -I m4 && autoconf && cd libltdl && autoconf)
done
changed() { diff "$1" "$2" | sed -n '/^[<>] /p'; }
for file in configure libltdl/configure; do
    name=$(echo "$file" | tr / _)
    changed "$work/unchanged/$file" "$work/maintained/$file" > "$work/$name.regenerated"
    changed "$work/original/$file" "$work/packaged/$file" > "$work/$name.shipped"
    [ -s "$work/$name.shipped" ] || { echo "No shipped change in $file" >&2; exit 1; }
    cmp "$work/$name.regenerated" "$work/$name.shipped" ||
        { echo "Shipped $file change differs from the macro change" >&2; exit 1; }
done
cd "$work/maintained"
./configure --prefix="$work/regeneration-only" > "$work/configure.log" 2>&1
make build-aux/ltmain.sh > "$work/ltmain.log" 2>&1
cmp build-aux/ltmain.sh "$work/packaged/build-aux/ltmain.sh"
echo 'PASS: pinned checksums, zero-fuzz source patches, repeated-patch rejection and generated changes equal to the macro changes'

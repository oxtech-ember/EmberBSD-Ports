#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), reproducible current GPG recipe selection.
set -eu
[ "$#" = 4 ] || { echo 'Usage: crypto-deps-source.sh DISTFILES PREPARED_PKGSRC CROSS_MAKECONF NEW_WORK' >&2; exit 2; }
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../../.." && pwd)
distfiles=$(CDPATH= cd -- "$1" && pwd)
prepared=$(CDPATH= cd -- "$2" && pwd)
conf=$3
mkdir "$4"
work=$(CDPATH= cd -- "$4" && pwd)
: "${BMAKE:?Set the native bmake executable}"
: "${DIGEST:?Set the native digest executable}"
mkdir "$work/pkgsrc" "$work/source"
git -C "$root/upstream/pkgsrc" archive --format=tar HEAD security/gnupg2 security/libassuan2 security/libgpg-error > "$work/recipes.tar"
tar -xf "$work/recipes.tar" -C "$work/pkgsrc"
patch -f -N -F 0 -p1 -d "$work/pkgsrc" < "$root/probes/plasma-mobile/toolkit/current-crypto-deps.patch"
for file in security/gnupg2/Makefile security/gnupg2/distinfo security/libassuan2/Makefile security/libgpg-error/buildlink3.mk; do
    cmp "$work/pkgsrc/$file" "$prepared/$file"
done
export DIGEST
verifier=$root/upstream/pkgsrc/mk/checksum/checksum.awk
(cd "$distfiles" && awk -f "$verifier" -- "$work/pkgsrc/security/gnupg2/distinfo" gnupg-2.5.24.tar.bz2)
tar -xf "$distfiles/gnupg-2.5.24.tar.bz2" --strip-components=1 -C "$work/source"
for patch_name in $(awk '/^SHA1 \(patch-/ { gsub(/[()]/,"",$2); print $2 }' "$work/pkgsrc/security/gnupg2/distinfo"); do
    awk -f "$verifier" -- -p "$work/pkgsrc/security/gnupg2/distinfo" "$work/pkgsrc/security/gnupg2/patches/$patch_name"
    patch -f -N -F 0 -p0 -d "$work/source" < "$work/pkgsrc/security/gnupg2/patches/$patch_name"
done
"$BMAKE" -C "$prepared/security/libassuan2" "MAKECONF=$conf" -V '${CONFIGURE_ENV:MGPGRT_CONFIG=*}' > "$work/cross.txt"
"$BMAKE" -C "$prepared/security/libassuan2" "MAKECONF=$conf" USE_CROSS_COMPILE=no -V '${CONFIGURE_ENV:MGPGRT_CONFIG=*}' > "$work/native.txt"
[ ! -s "$work/native.txt" ] || [ "$(cat "$work/native.txt")" = '' ]
sysroot=$("$BMAKE" -C "$prepared/security/libassuan2" "MAKECONF=$conf" -V '${CROSS_DESTDIR}')
prefix=$("$BMAKE" -C "$prepared/security/libassuan2" "MAKECONF=$conf" -V '${PREFIX}')
expected=GPGRT_CONFIG=$sysroot$prefix/bin/gpgrt-config
grep -Fxq "$expected" "$work/cross.txt"
selected=${expected#GPGRT_CONFIG=}
for option in --cflags --libs --variable=host; do
    "$selected" "--libdir=$sysroot$prefix/lib" gpg-error "$option" >> "$work/target-metadata.txt"
done
! grep -F "$sysroot" "$work/target-metadata.txt"
grep -q -- "-I$prefix/include" "$work/target-metadata.txt"
# The MAKECONF selects the target: aarch64 or x86_64.
arch=$("$BMAKE" -C "$prepared/security/libassuan2" "MAKECONF=$conf" -V '${MACHINE_GNU_ARCH}')
grep -Eq "^$arch-.*netbsd" "$work/target-metadata.txt"
if patch -f -N -F 0 -p1 -d "$work/pkgsrc" < "$root/probes/plasma-mobile/toolkit/current-crypto-deps.patch" > "$work/repeated.log" 2>&1; then exit 1; fi
rm "$work/recipes.tar"
echo 'PASS: current GnuPG archive, zero-fuzz source patch, exact export, target GPG metadata and unchanged native selection'

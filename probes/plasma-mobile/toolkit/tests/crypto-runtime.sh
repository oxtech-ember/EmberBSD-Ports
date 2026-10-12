#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), isolated installed GnuPG consumer.
set -eu
[ "$#" = 1 ] || { echo 'Usage: crypto-runtime.sh NEW_OUTPUT' >&2; exit 2; }
mkdir "$1"
work=$(CDPATH= cd -- "$1" && pwd)
PATH=/usr/pkg/bin:/usr/pkg/sbin:/usr/bin:/usr/sbin:/bin:/sbin; export PATH
umask 077
mkdir "$work/home"
GNUPGHOME=$work/home; export GNUPGHOME
trap 'timeout -k 5 15 gpgconf --homedir "$GNUPGHOME" --kill all' EXIT
sysctl kern.boottime > "$work/boot.before"
pkg_info -e gnupg2 > "$work/package.txt"
gpg --version > "$work/version.txt"
ldd /usr/pkg/bin/gpg > "$work/gpg.ldd"
! grep -q 'not found' "$work/gpg.ldd"
grep -q '/usr/pkg/lib/libgcrypt' "$work/gpg.ldd"
printf '%s\n' 'EmberBSD isolated GnuPG package test; no personal data or keys.' > "$work/plain.txt"
printf '%s\n' 'public-test-passphrase' | timeout -k 5 60 gpg --batch --pinentry-mode loopback \
    --passphrase-fd 0 --symmetric --cipher-algo AES256 --output "$work/cipher.gpg" \
    "$work/plain.txt" > "$work/encrypt.log" 2>&1
printf '%s\n' 'public-test-passphrase' | timeout -k 5 60 gpg --batch --no-symkey-cache --pinentry-mode loopback \
    --passphrase-fd 0 --decrypt --output "$work/decrypted.txt" "$work/cipher.gpg" \
    > "$work/decrypt.log" 2>&1
cmp "$work/plain.txt" "$work/decrypted.txt"
if printf '%s\n' 'deliberately-wrong-test-passphrase' | timeout -k 5 60 gpg --batch --no-symkey-cache \
    --pinentry-mode loopback --passphrase-fd 0 --decrypt --output "$work/wrong.txt" \
    "$work/cipher.gpg" > "$work/wrong.log" 2>&1; then
    echo 'Wrong passphrase was accepted' >&2; exit 1
fi
timeout -k 5 15 gpgconf --homedir "$GNUPGHOME" --kill all
sysctl kern.boottime > "$work/boot.after"
cmp "$work/boot.before" "$work/boot.after"
cat "$work/version.txt" "$work/decrypt.log"
echo 'PASS: installed GnuPG symmetric round trip and wrong-passphrase rejection; KWallet integration remains separate'

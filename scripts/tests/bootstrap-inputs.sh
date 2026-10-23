#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check the pkgsrc bootstrap inputs of an export.
# The bootstrap copies source trees from files/ directories and installs its
# packages without fetching. A recipe that replaces one of them must keep both.
# Set BMAKE to a host bmake to also check that each bootstrap package has no
# distfiles.
set -eu
[ "$#" = 1 ] || { echo "Usage: [BMAKE=/absolute/host/bin/bmake] $0 PREPARED_PKGSRC" >&2; exit 2; }
exported=$(CDPATH= cd -- "$1" && pwd)
script=$exported/bootstrap/bootstrap
[ -f "$script" ] || { echo "Missing bootstrap script: $script" >&2; exit 1; }
failed=0
fail() { echo "FAIL: $*" >&2; failed=1; }

sources=$(sed -n 's|^[[:space:]]*copy_src \$pkgsrcdir/\([^[:space:]]*\).*|\1|p' "$script" | LC_ALL=C sort -u)
[ -n "$sources" ] || fail 'no copy_src inputs found in bootstrap/bootstrap'
for source in $sources; do
    [ -d "$exported/$source" ] || { fail "missing bootstrap source: $source"; continue; }
    [ -n "$(ls -A "$exported/$source")" ] || fail "empty bootstrap source: $source"
done

# build_package installs with PKG_PRESERVE; these are the BOOTSTRAP_PKG packages.
packages=$(sed -n 's|^.*build_package "\([^"]*\)".*|\1|p' "$script" | LC_ALL=C sort -u)
[ -n "$packages" ] || fail 'no bootstrap packages found in bootstrap/bootstrap'
for package in $packages; do
    makefile=$exported/$package/Makefile
    [ -f "$makefile" ] || { fail "missing bootstrap package: $package"; continue; }
    grep -Eq '^BOOTSTRAP_PKG[?]?=[[:space:]]*yes' "$makefile" ||
        fail "$package does not set BOOTSTRAP_PKG=yes"
    if [ -n "${BMAKE:-}" ]; then
        distfiles=$("$BMAKE" -C "$exported/$package" -V '${DISTFILES}') ||
            { fail "cannot read DISTFILES of $package"; continue; }
        [ -z "$distfiles" ] || fail "$package needs distfiles ($distfiles); the bootstrap does not fetch"
    fi
done

# The first shell is built from the copied mksh sources with Build.sh.
mksh=$exported/shells/mksh/files
if grep -q 'copy_src \$pkgsrcdir/shells/mksh/files' "$script"; then
    [ -f "$mksh/Build.sh" ] || fail 'shells/mksh/files has no Build.sh'
    if grep -q 'USE_PRINTF_BUILTIN=1' "$script" && [ ! -f "$mksh/printf.c" ]; then
        fail 'bootstrap requests the printf builtin, but shells/mksh/files has no printf.c'
    fi
fi
[ "$failed" = 0 ] || exit 1
set -- $sources
count=$#
set -- $packages
printf 'PASS: %s bootstrap source trees and %s bootstrap packages are in the export\n' "$count" "$#"

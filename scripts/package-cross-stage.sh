#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Package a verified cross staging prefix.
set -eu
umask 022
[ "$#" = 4 ] || { echo 'Usage: package-cross-stage.sh STAGED_PREFIX RECIPE OUTPUT BUILD_INFO' >&2; exit 2; }
stage=$1 recipe=$2 package=$3 info=$4
[ "$(uname -s)" = NetBSD ] || exit 1
machine_arch=$(uname -p)
case "$machine_arch" in aarch64|x86_64) ;; *) exit 1;; esac
for path do case "$path" in /*) ;; *) echo 'Absolute paths required.' >&2; exit 2;; esac; done
[ -d "$stage" ] && [ -f "$recipe/PLIST" ] && [ -f "$recipe/DESCR" ] && [ -f "$info" ] || exit 1
[ "$(sed -n 's/^MACHINE_ARCH=//p' "$info")" = "$machine_arch" ] || {
    echo 'Package metadata does not match this execution architecture.' >&2; exit 1;
}
[ ! -e "$package" ] && [ ! -L "$package" ] || { echo 'Output path already exists.' >&2; exit 2; }
work=$(mktemp -d /tmp/cross-package.XXXXXXXX)
trap 'rm -rf "$work"' EXIT
trap 'exit 130' INT
trap 'exit 143' HUP TERM
sed '/^@comment/d' "$recipe/PLIST" | LC_ALL=C sort > "$work/expected"
(cd "$stage" && find . \( -type f -o -type l \) -print | sed 's|^\./||' | LC_ALL=C sort) > "$work/actual"
cmp "$work/expected" "$work/actual"
# Store real package dependencies in +CONTENTS as well as build metadata.
depends=$(sed -n 's/^DEPENDS=//p' "$info")
case "$depends" in *[!A-Za-z0-9_.+\ -]*) echo 'Invalid exact package dependency list.' >&2; exit 2;; esac
conflicts=$(sed -n 's/^CONFLICTS=//p' "$info")
if [ "$(sed -n '/^CONFLICTS=/p' "$info" | wc -l)" -gt 1 ]; then
    echo 'Invalid package conflict pattern list.' >&2; exit 2
fi
if [ -n "$conflicts" ]; then
    # Validate package patterns as data. Never expand globs or evaluate metadata.
    # This bounded syntax permits names, globs and version comparisons.
    printf '%s\n' "$conflicts" | LC_ALL=C awk '
    function valid(pattern, i, ch, bracket, count) {
        if (pattern !~ /^[A-Za-z0-9]/) return 0
        bracket = 0
        for (i = 1; i <= length(pattern); ++i) {
            ch = substr(pattern, i, 1)
            if (ch == "[") {
                if (bracket) return 0
                bracket = 1; count = 0
            } else if (ch == "]") {
                if (!bracket || !count) return 0
                bracket = 0
            } else if (bracket) {
                if (!index("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!-", ch)) return 0
                ++count
            } else if (!index("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.+*?<>!=-", ch)) return 0
        }
        return !bracket
    }
    {
        if (NR != 1 || NF == 0) bad = 1
        for (field = 1; field <= NF; ++field)
            if (!valid($field)) bad = 1
    }
    END { exit (bad || NR != 1) }
    ' || { echo 'Invalid package conflict pattern list.' >&2; exit 2; }
fi
set -- pkg_create -u root -g wheel -p "$stage" -I /usr/pkg \
    -c '-EmberBSD cross-built package' -d "$recipe/DESCR" \
    -f "$recipe/PLIST" -B "$info" -P "$depends"
if [ -n "$conflicts" ]; then set -- "$@" -C "$conflicts"; fi
"$@" "$package"
[ -s "$package" ]
pkg_info -B "$package"

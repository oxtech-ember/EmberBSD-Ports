#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Verify and install a prepared runtime package set.
set -eu
umask 077
LC_ALL=C
export LC_ALL
fail() { echo "FAIL: $*" >&2; exit 1; }
# Keep verification data private. Package directories must allow normal users.
install_archive() {
    (umask 022; "$add" -U "$@")
}
# Preserve the target's choices. Only new dependencies default to automatic.
install_package() (
    package=$1
    shift
    automatic=no
    if ! grep -Fx "$package" "$work/roots.txt" >/dev/null; then
        automatic=yes
        # pkg_add replaces the exact installed version first, then the best
        # installed version of the same base name.
        if installed=$("$info" -E "$package" || "$info" -E "${package%-*}"); then
            automatic=$("$info" -q -Q automatic "$installed") || return
            case $automatic in
                [Yy][Ee][Ss]) automatic=yes ;;
                ''|[Nn][Oo]) automatic=no ;;
                *) echo "Invalid automatic mark: $installed" >&2; return 1 ;;
            esac
        else
            status=$?
            [ "$status" = 1 ] || return "$status"
        fi
    fi
    if [ "$automatic" = yes ]; then
        install_archive -A "$@" || return
    else
        install_archive "$@" || return
        # -U preserves the previous mark, including automatic roots.
        "$admin" unset automatic "$package" || return
    fi
)
usage() {
    echo "Usage: $0 [--target aarch64|amd64] [--verify-only] PACKAGE_SET" >&2
    echo "       $0 [--target aarch64|amd64] --install PACKAGE_SET NEW_LOG" >&2
    exit 2
}
mode=verify
target=aarch64 target_seen=no mode_seen=no
while [ "$#" -gt 0 ]; do
    case $1 in
        --target)
            [ "$#" -ge 2 ] && [ -n "$2" ] && [ "$target_seen" = no ] || usage
            target=$2 target_seen=yes
            shift 2 ;;
        --verify-only|--install)
            [ "$mode_seen" = no ] || usage
            mode_seen=yes
            [ "$1" != --install ] || mode=install
            shift ;;
        --*) usage ;;
        *) break ;;
    esac
done
case $target in
    aarch64) machine_arch=aarch64 ;;
    amd64) machine_arch=x86_64 ;;
    *) fail "Unsupported target: $target" ;;
esac
if [ "$mode" = install ]; then [ "$#" = 2 ] || usage; else [ "$#" = 1 ] || usage; fi
bundle=$(CDPATH= cd -- "$1" && pwd -P)
log=${2:-}
for name in packages.sha256 install-order.txt roots.txt target.txt; do
    [ -f "$bundle/$name" ] && [ ! -L "$bundle/$name" ] || fail "Missing regular $name"
done
[ -d "$bundle/packages" ] && [ ! -L "$bundle/packages" ] || fail 'Missing regular packages directory'
info=${PKG_INFO:-pkg_info}
admin=${PKG_ADMIN:-pkg_admin}
command -v "$info" >/dev/null || fail 'pkg_info is required'
command -v "$admin" >/dev/null || fail 'pkg_admin is required'
work=$(mktemp -d "${TMPDIR:-/tmp}/ember-install-set.XXXXXXXX")
trap 'rm -rf "$work"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
mkdir "$work/pkgdb"
for name in packages.sha256 install-order.txt roots.txt target.txt; do
    cp "$bundle/$name" "$work/$name"
    [ -s "$work/$name" ] || fail "Empty manifest: $name"
    [ "$(tail -c 1 "$work/$name" | od -An -tu1 | tr -d ' ' | sed 's/^0*//')" = 10 ] || fail "Manifest needs a final newline: $name"
done
printf 'OPSYS=NetBSD\nOS_VERSION=11.0\nMACHINE_ARCH=%s\nOBJECT_FMT=ELF\n' "$machine_arch" > "$work/expected-target.txt"
cmp -s "$work/target.txt" "$work/expected-target.txt" || fail 'Target receipt mismatch'
# A strict name grammar makes manifests unambiguous on both BSD and macOS.
awk '
    !/^[a-zA-Z0-9][a-zA-Z0-9_.+-]*-[0-9][a-zA-Z0-9_.+-]*\.tgz$/ || seen[$0]++ { bad=1 }
    END { if (bad || NR == 0) exit 1 }
' "$work/install-order.txt" || fail 'Invalid or duplicate install-order entry'
awk '
    {
        if (length($1) != 64 || $1 !~ /^[0-9a-f]+$/ || NF != 2 ||
            $2 !~ /^packages\/[a-zA-Z0-9][a-zA-Z0-9_.+-]*-[0-9][a-zA-Z0-9_.+-]*\.tgz$/ ||
            $0 != $1 "  " $2 || seen[$2]++) { bad=1; next }
        sub(/^packages\//, "", $2); print $2
    }
    END { if (bad || NR == 0) exit 1 }
' "$work/packages.sha256" > "$work/hash-names" || fail 'Invalid or duplicate checksum entry'
sort "$work/install-order.txt" > "$work/order-sorted"
sort "$work/hash-names" > "$work/hash-sorted"
cmp -s "$work/order-sorted" "$work/hash-sorted" || fail 'Checksum and installation manifests differ'
: > "$work/archive-names"
for path in "$bundle/packages/"* "$bundle/packages/".[!.]* "$bundle/packages/"..?*; do
    [ -e "$path" ] || [ -L "$path" ] || continue
    [ -f "$path" ] && [ ! -L "$path" ] || fail "Not a regular package archive: $path"
    printf '%s\n' "${path##*/}" >> "$work/archive-names"
done
sort "$work/archive-names" > "$work/archive-sorted"
cmp -s "$work/order-sorted" "$work/archive-sorted" || fail 'Package directory and installation manifest differ'
awk '
    FILENAME == ARGV[1] { sub(/\.tgz$/, ""); packages[$0]=1; next }
    !/^[a-zA-Z0-9][a-zA-Z0-9_.+-]*-[0-9][a-zA-Z0-9_.+-]*$/ || !packages[$0] || seen[$0]++ { bad=1 }
    FILENAME == ARGV[2] { roots++ }
    END { if (bad || roots == 0) exit 1 }
' "$work/install-order.txt" "$work/roots.txt" || fail 'Invalid, missing or duplicate root package'
if command -v sha256 >/dev/null; then
    hash_file() { sha256 -q "$1"; }
elif command -v shasum >/dev/null; then
    hash_file() { shasum -a 256 "$1" | awk '{ print $1 }'; }
else
    fail 'sha256 or shasum is required'
fi
# Finish all byte-integrity checks before reading metadata or invoking pkg_add.
while read -r expected relative; do
    actual=$(hash_file "$bundle/$relative") || fail "Cannot hash $relative"
    [ "$actual" = "$expected" ] || fail "SHA256 mismatch: $relative"
done < "$work/packages.sha256"
: > "$work/dependencies"
while IFS= read -r archive; do
    name=${archive%.tgz}
    mkdir "$work/pkgdb/$name"
    "$info" -q -f "$bundle/packages/$archive" > "$work/pkgdb/$name/+CONTENTS" || fail "Cannot read package manifest: $archive"
    awk -v name="$name" '/^@name / { count++; if ($0 != "@name " name) bad=1 } END { exit bad || count != 1 }' \
        "$work/pkgdb/$name/+CONTENTS" || fail "Package identity differs: $archive"
    "$info" -q -B "$bundle/packages/$archive" > "$work/build-info" || fail "Cannot read target metadata: $archive"
    awk -F= -v machine_arch="$machine_arch" '
        $1 == "OPSYS" { os++; bad=bad || $0 != "OPSYS=NetBSD" }
        $1 == "OS_VERSION" { version++; bad=bad || $0 != "OS_VERSION=11.0" }
        $1 == "MACHINE_ARCH" { arch++; bad=bad || $0 != "MACHINE_ARCH=" machine_arch }
        $1 == "OBJECT_FMT" { object++; bad=bad || $0 != "OBJECT_FMT=ELF" }
        END { exit bad || os != 1 || version != 1 || arch != 1 || object != 1 }
    ' "$work/build-info" || fail "Package is not the prepared EmberBSD ABI: $archive"
    awk -v name="$name" '/^@pkgdep / { sub(/^@pkgdep /, ""); print name "\t" $0 }' \
        "$work/pkgdb/$name/+CONTENTS" >> "$work/dependencies"
done < "$work/install-order.txt"
cut -f2- "$work/dependencies" | sort -u > "$work/patterns"
: > "$work/resolved"
while IFS= read -r pattern; do
    [ -n "$pattern" ] || fail 'Empty dependency pattern'
    "$info" -K "$work/pkgdb" -e "$pattern" > "$work/matches" || fail "Missing dependency: $pattern"
    [ "$(wc -l < "$work/matches" | tr -d ' ')" = 1 ] || fail "Ambiguous dependency: $pattern"
    IFS= read -r matched < "$work/matches"
    "$admin" pmatch "$pattern" "$matched" || fail "Dependency pattern mismatch: $pattern"
    printf '%s\t%s\n' "$pattern" "$matched" >> "$work/resolved"
done < "$work/patterns"
awk -F '\t' '
    FILENAME == ARGV[1] { sub(/\.tgz$/, ""); position[$0]=FNR; next }
    FILENAME == ARGV[2] { resolved[$1]=$2; next }
    { selected=resolved[$2]; if (!position[selected] || position[selected] >= position[$1]) {
        print "Dependency must precede " $1 ": " $2 > "/dev/stderr"; bad=1
    } }
    END { exit bad }
' "$work/install-order.txt" "$work/resolved" "$work/dependencies" || fail 'Invalid dependency order'
count=$(wc -l < "$work/install-order.txt" | tr -d ' ')
echo "PASS: $count archives, SHA256, target metadata, roots and dependency order verified"
[ "$mode" = install ] || exit 0
case $(uname -s) in NetBSD|EmberBSD) ;; *) fail 'Installation requires an EmberBSD target' ;; esac
[ "$(uname -p)" = "$machine_arch" ] || fail "Installation requires $machine_arch"
[ "$(id -u)" = 0 ] || fail 'Installation requires root'
command -v pgrep >/dev/null || fail 'pgrep is required'
if pgrep -x plasmashell > "$work/plasmashell"; then
    fail 'Stop the active Plasma shell before package installation'
else
    status=$?
    [ "$status" = 1 ] || fail 'Cannot inspect active Plasma processes'
fi
add=${PKG_ADD:-pkg_add}
command -v "$add" >/dev/null || fail 'pkg_add is required'
[ ! -e "$log" ] && [ ! -L "$log" ] || fail 'Installation log already exists'
# Stop here on any package failure. Never start a session automatically.
(set -C; : > "$log") || fail 'Cannot create installation log'
exec >> "$log" 2>&1
date -u
printf 'Verified set: %s\nPackages: %s\n' "$bundle" "$count"
"$add" -V
"$admin" -V
cat "$work/packages.sha256"
PKG_PATH=$bundle/packages
export PKG_PATH
while IFS= read -r archive; do
    # Recheck immediately before installation if the package set was modified.
    expected=$(awk -v name="packages/$archive" '$2 == name {print $1}' "$work/packages.sha256")
    [ "$(hash_file "$bundle/packages/$archive")" = "$expected" ] || fail "Archive changed after verification: $archive"
    echo "Installing $archive"
    install_package "${archive%.tgz}" "$bundle/packages/$archive" || fail "Package installation failed: $archive"
done < "$work/install-order.txt"
set --
while IFS= read -r archive; do
    set -- "$@" "${archive%.tgz}"
done < "$work/install-order.txt"
"$admin" check "$@" || fail 'Installed package checks failed'
echo 'PASS: package installation and installed-file checks; desktop session not started'

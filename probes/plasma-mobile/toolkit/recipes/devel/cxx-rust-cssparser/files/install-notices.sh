#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Verify every original notice before creating the package destination.
set -eu
[ "$#" -ge 5 ] || { echo "Usage: $0 SOURCE DESTINATION MANIFEST NATIVE_DIGEST INSTALL [ARGS...]" >&2; exit 2; }
source=$1 destination=$2 manifest=$3 digest=$4
shift 4
fail() { echo "CSS parser notices: $*" >&2; exit 1; }
case "$source:$destination:$manifest:$digest" in /*:/*:/*:/*) ;; *) fail 'absolute paths required' ;; esac
source=${source%/}
[ -n "$source" ] || fail 'source cannot be filesystem root'
[ -d "$source" ] && [ ! -L "$source" ] || fail 'invalid source directory'
[ -f "$manifest" ] && [ ! -L "$manifest" ] || fail 'invalid notice manifest'
[ ! -e "$destination" ] && [ ! -L "$destination" ] || fail 'destination already exists'
[ -x "$digest" ] || fail 'native digest tool required'
for path in "$source" "$destination" "$manifest"; do
    component=$path
    while [ -n "$component" ]; do
        [ ! -L "$component" ] || fail "symlink path: $path"
        component=${component%/*}
    done
done
# Only safe relative original file paths occur in the checked-in manifest.
awk -F '\t' '
    NF != 2 || length($1) != 64 || $1 ~ /[^0-9a-f]/ ||
    $2 !~ /^(project|vendor)\// || $2 ~ /[^A-Za-z0-9_.\/+-]/ ||
    $2 ~ /(^|\/)\.\.?($|\/)/ || $2 ~ /\/\// || $2 ~ /\/$/ || seen[$2]++ {exit 1}
    END {if (NR == 0) exit 1}
' "$manifest" || fail 'invalid or duplicate notice manifest entry'
tab=$(printf '\t')
while IFS="$tab" read -r expected relative || [ -n "$expected$relative" ]; do
    case "$relative" in
        project/*) file=$source/${relative#project/} ;;
        vendor/*) file=$source/rust/$relative ;;
    esac
    # Reject symlink ancestors as well as symlink final components.
    component=$file
    while [ "$component" != "$source" ]; do
        [ ! -L "$component" ] || fail "symlink source: $relative"
        component=${component%/*}
    done
    [ -f "$file" ] || fail "missing original notice: $relative"
    actual=$("$digest" SHA256 "$file") || fail "cannot hash original notice: $relative"
    actual=${actual##* }
    [ "$actual" = "$expected" ] || fail "changed original notice: $relative"
done < "$manifest"
# All inputs passed. Use the caller's normal pkgsrc INSTALL_DATA command.
mkdir -p "$destination"
while IFS="$tab" read -r expected relative || [ -n "$expected$relative" ]; do
    case "$relative" in
        project/*) file=$source/${relative#project/} ;;
        vendor/*) file=$source/rust/$relative ;;
    esac
    mkdir -p "$destination/${relative%/*}"
    "$@" "$file" "$destination/$relative"
done < "$manifest"

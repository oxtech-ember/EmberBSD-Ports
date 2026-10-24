#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# Build a list of pkgsrc packages in dependency order with the cross MAKECONF.
#
#   order  Find all dependencies of the list and sort them. Writes STATE/order.
#   fetch  Get the distfiles for STATE/order. Only network and DISTDIR.
#   build  Build and install each package in STATE/order.
#
# A built package is recorded in STATE/done with its PKGNAME and SHA256.
# The build skips a package if the record and the package file agree.
# Failures go to STATE/failed. Packages with a failed dependency go to
# STATE/blocked. Logs are in STATE/logs.
set -eu
umask 022

[ "$#" -eq 3 ] || {
    echo 'Usage: sh scripts/cross-bulk.sh order|fetch|build PKGPATH_LIST ABSOLUTE_STATE' >&2
    exit 2
}
mode=$1
list=$2
state=$3
case "$state" in
    /*) ;;
    *) echo "Not an absolute path: $state" >&2; exit 2 ;;
esac
: "${BMAKE:?Set BMAKE to the host bmake}"
: "${MAKECONF:?Set MAKECONF to the cross MAKECONF}"
: "${PKGSRCDIR:?Set PKGSRCDIR to the prepared pkgsrc tree}"
export MAKECONF
mkdir -p "$state/logs"

var()
{
    "$BMAKE" -C "$PKGSRCDIR/$1" show-var VARNAME="$2" < /dev/null
}

# Print the target dependency paths of one package. Tool dependencies are
# native host packages; pkgsrc builds them itself.
target_deps()
{
    "$BMAKE" -C "$PKGSRCDIR/$1" show-vars VARNAMES='DEPENDS BUILD_DEPENDS' < /dev/null |
        tr ' ' '\n' | sed -n 's|^.*:\.\./\.\./\([^/]*/[^/]*\)$|\1|p' | sort -u
}

order()
{
    : > "$state/edges.new"
    sort -u "$list" > "$state/queue"
    : > "$state/seen"
    while [ -s "$state/queue" ]; do
        : > "$state/next"
        while read -r path; do
            grep -qFx "$path" "$state/seen" && continue
            echo "$path" >> "$state/seen"
            echo "$path $path" >> "$state/edges.new"
            target_deps "$path" > "$state/deps" 2>> "$state/logs/order.err" || {
                echo "$path order" >> "$state/failed"
                continue
            }
            while read -r dep; do
                [ -n "$dep" ] || continue
                echo "$dep $path" >> "$state/edges.new"
                echo "$dep" >> "$state/next"
            done < "$state/deps"
        done < "$state/queue"
        sort -u "$state/next" > "$state/queue"
    done
    tsort "$state/edges.new" > "$state/order.new"
    mv "$state/edges.new" "$state/edges"
    mv "$state/order.new" "$state/order"
    rm -f "$state/queue" "$state/next" "$state/deps"
    echo "Ordered $(wc -l < "$state/order") packages: $state/order"
}

fetch()
{
    while read -r path; do
        log=$state/logs/fetch-$(echo "$path" | tr / _).log
        "$BMAKE" -C "$PKGSRCDIR/$path" fetch < /dev/null > "$log" 2>&1 ||
            echo "$path fetch" >> "$state/failed-fetch"
    done < "$state/order"
}

build()
{
    # Keep the results of an earlier run, but try its failures again.
    stamp=$(date '+%Y%m%d%H%M%S')
    for list_name in failed blocked; do
        [ -s "$state/$list_name" ] && mv "$state/$list_name" "$state/$list_name.$stamp"
    done
    touch "$state/done" "$state/failed" "$state/blocked"
    packages=$(var pkgtools/pkg_install PACKAGES)/All
    while read -r path; do
        name=$(var "$path" PKGNAME) || { echo "$path vars" >> "$state/failed"; continue; }
        file=$packages/$name.tgz
        if [ -f "$file" ] && grep -qFx "$path $name $(shasum -a 256 "$file" | cut -d ' ' -f 1)" "$state/done"; then
            continue
        fi
        bad=$(awk -v p="$path" '$2 == p && $1 != p { print $1 }' "$state/edges" |
            while read -r dep; do
                cat "$state/failed" "$state/blocked" | awk -v d="$dep" '$1 == d { found = 1 } END { exit !found }' && echo "$dep"
            done | head -n 1)
        if [ -n "$bad" ]; then
            echo "$path $bad" >> "$state/blocked"
            continue
        fi
        log=$state/logs/$(echo "$path" | tr / _).log
        echo "$(date '+%Y-%m-%d %H:%M:%S') start $path $name" >> "$state/progress"
        # Go module caches are read-only; make an old WRKDIR removable first.
        wrkdir=$("$BMAKE" -C "$PKGSRCDIR/$path" show-var VARNAME=WRKDIR < /dev/null 2>/dev/null) || wrkdir=
        case "$wrkdir" in /*) [ ! -d "$wrkdir" ] || chmod -R u+w "$wrkdir" ;; esac
        if "$BMAKE" -C "$PKGSRCDIR/$path" clean < /dev/null > "$log" 2>&1 &&
            "$BMAKE" -C "$PKGSRCDIR/$path" package-install < /dev/null >> "$log" 2>&1; then
            echo "$path $name $(shasum -a 256 "$file" | cut -d ' ' -f 1)" >> "$state/done"
            echo "$(date '+%Y-%m-%d %H:%M:%S') done $path" >> "$state/progress"
        else
            echo "$path build" >> "$state/failed"
            echo "$(date '+%Y-%m-%d %H:%M:%S') FAILED $path" >> "$state/progress"
        fi
    done < "$state/order"
}

case "$mode" in
    order) order ;;
    fetch) fetch ;;
    build) build ;;
    *) echo "Unknown mode: $mode" >&2; exit 2 ;;
esac

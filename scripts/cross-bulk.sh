#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# Build a list of pkgsrc packages in dependency order with the cross MAKECONF.
#
#   order  Find all dependencies of the list and sort them. Writes STATE/order.
#          List entries the profile skips (PKG_SKIP_REASON) go to
#          STATE/skipped. A graph in which a package reaches a skipped
#          package is refused: no order is written.
#   fetch  Get the distfiles for STATE/order. Only network and DISTDIR.
#   build  Build and install each package in STATE/order.
#
# The build options of target dependencies that are not installed come
# from the tree (mk/pkg-build-options.mk). Order starts a new pkgsrc
# PBULK_CACHE_DIRECTORY in STATE/build-options, as a pbulk scan does.
# Fetch reuses it only while the tree, the MAKECONF and the native
# selection are those of that order run. Build does not use it: there
# the installed dependencies answer the query.
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

# Verify the selected native prefix once per run. Every later bmake call,
# and its recursive queries, receive the verified selection on the command
# line and skip the per-parse verifier.
unset EMBERBSD_NATIVE_TOOLSET_VERIFIED
native=$("$BMAKE" -C "$PKGSRCDIR/pkgtools/pkg_install" show-var \
    VARNAME=EMBERBSD_NATIVE_TOOLSET_VERIFIED < /dev/null) || {
    echo 'The native host prefix selection failed verification' >&2
    exit 2
}
[ -n "$native" ] || { echo 'The MAKECONF has no native host prefix selection' >&2; exit 2; }

cache=$state/build-options
cachearg=

mk()
{
    "$BMAKE" EMBERBSD_NATIVE_TOOLSET_VERIFIED="$native" \
        ${cachearg:+"PBULK_CACHE_DIRECTORY=$cachearg"} "$@"
}

# The inputs of the cached build options: the native selection, the tree
# directory itself, so a replaced export does not match, and the content of
# each absolute makefile that a parse reads: the MAKECONF, its includes and
# the generated files at the top of the tree.
cache_identity()
{
    files=$(var pkgtools/pkg_install .MAKE.MAKEFILES) || return 1
    printf '%s\n' "$PKGSRCDIR" "$native"
    ls -id "$PKGSRCDIR/" | awk '{ print $1 }'
    for file in $files; do
        case "$file" in /*) shasum -a 256 "$file" || return 1 ;; esac
    done
}

new_cache()
{
    rm -rf "$cache"
    mkdir "$cache"
    cache_identity > "$cache/identity" || { rm -rf "$cache"; return 0; }
    cachearg=$cache
}

# Use the order cache only with the same inputs, and if no file in mk/ or
# in an ordered package directory changed after the order run started.
reuse_cache()
{
    if [ -f "$cache/identity" ] && cache_identity > "$state/identity" &&
        cmp -s "$state/identity" "$cache/identity" &&
        [ -z "$(cd "$PKGSRCDIR" && find mk $(cat "$state/order") -newer "$cache/identity" -print | head -n 1)" ]; then
        cachearg=$cache
    else
        echo 'The build options cache is not from this tree; querying without it' >&2
    fi
    rm -f "$state/identity"
}

var()
{
    mk -C "$PKGSRCDIR/$1" show-var VARNAME="$2" < /dev/null
}

# Print the target dependency paths of one package and write its
# PKG_SKIP_REASON to STATE/skip. Tool dependencies are native host
# packages; pkgsrc builds them itself.
target_deps()
{
    mk -C "$PKGSRCDIR/$1" show-vars VARNAMES='PKG_SKIP_REASON DEPENDS BUILD_DEPENDS' \
        < /dev/null > "$state/vars" || return 1
    sed -n '1p' "$state/vars" > "$state/skip"
    sed '1d' "$state/vars" |
        tr ' ' '\n' | sed -n 's|^.*:\.\./\.\./\([^/]*/[^/]*\)$|\1|p' | sort -u
}

order()
{
    new_cache
    : > "$state/edges.new"
    : > "$state/skipped.new"
    sort -u "$list" > "$state/queue"
    : > "$state/seen"
    while [ -s "$state/queue" ]; do
        : > "$state/next"
        while read -r path; do
            grep -qFx "$path" "$state/seen" && continue
            echo "$path" >> "$state/seen"
            target_deps "$path" > "$state/deps" 2>> "$state/logs/order.err" || {
                echo "$path $path" >> "$state/edges.new"
                echo "$path order" >> "$state/failed"
                continue
            }
            if [ -n "$(cat "$state/skip")" ]; then
                echo "$path $(cat "$state/skip")" >> "$state/skipped.new"
                continue
            fi
            echo "$path $path" >> "$state/edges.new"
            while read -r dep; do
                [ -n "$dep" ] || continue
                echo "$dep $path" >> "$state/edges.new"
                echo "$dep" >> "$state/next"
            done < "$state/deps"
        done < "$state/queue"
        sort -u "$state/next" > "$state/queue"
    done
    rm -f "$state/vars" "$state/skip"
    # A skipped package is outside this profile; nothing may depend on it.
    refused=$(awk 'FILENAME == ARGV[1] { skip[$1] = 1; next } ($1 in skip) && $1 != $2 { print $2 " -> " $1 }' \
        "$state/skipped.new" "$state/edges.new")
    if [ -n "$refused" ]; then
        echo 'Refused: these packages depend on packages the profile skips:' >&2
        echo "$refused" >&2
        return 1
    fi
    mv "$state/skipped.new" "$state/skipped"
    tsort "$state/edges.new" > "$state/order.new"
    mv "$state/edges.new" "$state/edges"
    mv "$state/order.new" "$state/order"
    rm -f "$state/queue" "$state/next" "$state/deps"
    echo "Ordered $(wc -l < "$state/order") packages: $state/order; skipped $(wc -l < "$state/skipped")"
}

fetch()
{
    reuse_cache
    while read -r path; do
        log=$state/logs/fetch-$(echo "$path" | tr / _).log
        mk -C "$PKGSRCDIR/$path" fetch < /dev/null > "$log" 2>&1 ||
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
        vars=$(mk -C "$PKGSRCDIR/$path" show-vars VARNAMES='PKGNAME WRKDIR' < /dev/null) ||
            { echo "$path vars" >> "$state/failed"; continue; }
        name=$(printf '%s\n' "$vars" | sed -n 1p)
        wrkdir=$(printf '%s\n' "$vars" | sed -n 2p)
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
        case "$wrkdir" in /*) [ ! -d "$wrkdir" ] || chmod -R u+w "$wrkdir" ;; esac
        if mk -C "$PKGSRCDIR/$path" clean < /dev/null > "$log" 2>&1 &&
            mk -C "$PKGSRCDIR/$path" package-install < /dev/null >> "$log" 2>&1; then
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

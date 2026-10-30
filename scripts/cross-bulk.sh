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
#          A package whose distinfo distfiles are all in DISTDIR with
#          their recorded sizes is not queried; the build verifies the
#          checksums.
#   build  Build and install each package in STATE/order, several at once
#          (CROSS_BULK_JOBS, see build below).
#
# Fetch and build check PKG_SKIP_REASON again before they act on a package:
# an order written by an older tree or by hand may name a package that the
# profile now skips. Such a package goes to STATE/skipped, never to a
# failure list, and the packages that depend on it are blocked.
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

# True if the distinfo of a package lists distfiles and DISTDIR has each
# with its recorded size. A package without distinfo asks bmake.
have_distfiles()
{
    [ -f "$PKGSRCDIR/$1/distinfo" ] || return 1
    awk '$1 == "Size" && $3 == "=" && NF == 5 { sub(/^\(/, "", $2); sub(/\)$/, "", $2); print $2, $4; n++ }
        END { exit !n }' "$PKGSRCDIR/$1/distinfo" > "$state/sizes" || return 1
    while read -r file size; do
        [ -f "$distdir/$file" ] && [ "$(wc -c < "$distdir/$file" | tr -d ' ')" = "$size" ] || return 1
    done < "$state/sizes"
}

fetch()
{
    reuse_cache
    distdir=$(var pkgtools/pkg_install DISTDIR)
    case "$distdir" in /*) ;; *) echo "DISTDIR is not absolute: $distdir" >&2; return 1 ;; esac
    while read -r path; do
        have_distfiles "$path" && continue
        skip=$(var "$path" PKG_SKIP_REASON) || skip=
        if [ -n "$skip" ]; then
            echo "$path $skip" >> "$state/skipped"
            continue
        fi
        log=$state/logs/fetch-$(echo "$path" | tr / _).log
        mk -C "$PKGSRCDIR/$path" fetch < /dev/null > "$log" 2>&1 ||
            echo "$path fetch" >> "$state/failed-fetch"
    done < "$state/order"
    rm -f "$state/sizes"
}

# Package-level parallelism. CROSS_BULK_JOBS packages build at once (default:
# half the host CPUs). Each gets MAKE_JOBS=CROSS_BULK_MAKE_JOBS on the command
# line (default: 1.5 x CPUs split over the packages, at most the CPUs), which
# also reaches pkgsrc's dependency recursion; MAKE_JOBS_SAFE=no recipes stay
# serial. CROSS_BULK_MAKE_JOBS=makeconf leaves MAKE_JOBS to the MAKECONF.
# CROSS_BULK_CPUS overrides the detected CPU count.
host_cpus()
{
    n=${CROSS_BULK_CPUS:-$(sysctl -n hw.ncpu 2>/dev/null || getconf _NPROCESSORS_ONLN 2>/dev/null || echo 1)}
    case "$n" in ''|*[!0-9]*|0) n=1 ;; esac
    echo "$n"
}

count()
{
    case "$2" in ''|*[!0-9]*|0) echo "$1 must be a positive number: $2" >&2; exit 2 ;; esac
}

# A package starts only when every target dependency in STATE/edges is done.
# Only the scheduler writes the state files; a package reports its result in
# STATE/run/KEY.result, written to a temporary name and renamed. Dependency
# installs (pkgsrc depends, which may build native tools into the shared host
# prefix) and the final package install run under STATE/install.lock, a
# directory lock, which works on macOS, NetBSD and Linux alike.
locked()
{
    until mkdir "$state/install.lock" 2> /dev/null; do
        sleep 1
    done
    rc=0
    "$@" || rc=$?
    rmdir "$state/install.lock"
    return "$rc"
}

bmk()
{
    if [ "$make_jobs" = makeconf ]; then
        mk "$@"
    else
        mk MAKE_JOBS="$make_jobs" "$@"
    fi
}

result()
{
    printf '%s\n' "$2" > "$run/$1.tmp"
    mv "$run/$1.tmp" "$run/$1.result"
}

build_one()
{
    path=$1
    key=$(echo "$path" | tr / _)
    vars=$(bmk -C "$PKGSRCDIR/$path" show-vars VARNAMES='PKGNAME WRKDIR PKG_SKIP_REASON' < /dev/null) ||
        { result "$key" "failed $path vars"; return 0; }
    name=$(printf '%s\n' "$vars" | sed -n 1p)
    wrkdir=$(printf '%s\n' "$vars" | sed -n 2p)
    skip=$(printf '%s\n' "$vars" | sed -n 3p)
    if [ -n "$skip" ]; then
        result "$key" "skipped $path $skip"
        return 0
    fi
    file=$packages/$name.tgz
    if [ -f "$file" ] && grep -qFx "$path $name $(shasum -a 256 "$file" | cut -d ' ' -f 1)" "$state/done"; then
        result "$key" "done $path"
        return 0
    fi
    log=$state/logs/$key.log
    # One short line per append: O_APPEND keeps concurrent lines whole.
    echo "$(date '+%Y-%m-%d %H:%M:%S') start $path $name" >> "$state/progress"
    # Go module caches are read-only; make an old WRKDIR removable first.
    case "$wrkdir" in /*) [ ! -d "$wrkdir" ] || chmod -R u+w "$wrkdir" ;; esac
    if [ "$workers" -eq 1 ]; then
        bmk -C "$PKGSRCDIR/$path" clean < /dev/null > "$log" 2>&1 &&
            bmk -C "$PKGSRCDIR/$path" package-install < /dev/null >> "$log" 2>&1
    else
        bmk -C "$PKGSRCDIR/$path" clean < /dev/null > "$log" 2>&1 &&
            locked bmk -C "$PKGSRCDIR/$path" depends < /dev/null >> "$log" 2>&1 &&
            bmk -C "$PKGSRCDIR/$path" package < /dev/null >> "$log" 2>&1 &&
            locked bmk -C "$PKGSRCDIR/$path" package-install < /dev/null >> "$log" 2>&1
    fi && {
        echo "$(date '+%Y-%m-%d %H:%M:%S') done $path" >> "$state/progress"
        result "$key" "built $path $name $(shasum -a 256 "$file" | cut -d ' ' -f 1)"
        return 0
    }
    echo "$(date '+%Y-%m-%d %H:%M:%S') FAILED $path" >> "$state/progress"
    result "$key" "failed $path build"
}

# Print "R PATH" for up to $1 packages whose dependencies are all done and
# "B PATH DEP" for packages with a failed, blocked or skipped dependency.
ready()
{
    awk -v max="$1" '
        FILENAME == ARGV[1] { st[$1] = $2; next }
        FILENAME == ARGV[2] { if ($1 != $2) deps[$2] = deps[$2] " " $1; next }
        { order[++n] = $1; listed[$1] = 1 }
        END {
            for (i = 1; i <= n; i++) {
                p = order[i]
                if (p in st) continue
                k = split(deps[p], d, " ")
                bad = ""; wait = 0
                for (j = 1; j <= k; j++) {
                    s = st[d[j]]
                    if (s == "failed" || s == "blocked" || s == "skipped") { bad = d[j]; break }
                    if (s != "done" && (d[j] in listed)) wait = 1
                }
                if (bad != "") { print "B", p, bad; st[p] = "blocked"; continue }
                if (!wait && started < max) { print "R", p; started++; st[p] = "running" }
            }
        }' "$run/status" "$state/edges" "$state/order"
}

build()
{
    cpus=$(host_cpus)
    workers=${CROSS_BULK_JOBS:-$(( (cpus + 1) / 2 ))}
    count CROSS_BULK_JOBS "$workers"
    make_jobs=${CROSS_BULK_MAKE_JOBS:-$(( (3 * cpus + 2 * workers - 1) / (2 * workers) ))}
    if [ "$make_jobs" != makeconf ]; then
        count CROSS_BULK_MAKE_JOBS "$make_jobs"
        [ -n "${CROSS_BULK_MAKE_JOBS:-}" ] || [ "$make_jobs" -le "$cpus" ] || make_jobs=$cpus
    fi
    run=$state/run
    # One scheduler per state directory.
    if ! mkdir "$state/build.lock" 2> /dev/null; then
        other=$(cat "$state/build.lock/pid" 2> /dev/null || :)
        if [ -n "$other" ] && kill -0 "$other" 2> /dev/null; then
            echo "Another build ($other) uses $state" >&2
            exit 2
        fi
    fi
    echo $$ > "$state/build.lock/pid"
    # Locks and results of an interrupted run; its packages are rebuilt.
    rm -rf "$run" "$state/install.lock"
    mkdir "$run"
    : > "$run/status"
    # Keep the results of an earlier run, but try its failures again.
    stamp=$(date '+%Y%m%d%H%M%S')
    for list_name in failed blocked; do
        [ -s "$state/$list_name" ] && mv "$state/$list_name" "$state/$list_name.$stamp"
    done
    touch "$state/done" "$state/failed" "$state/blocked" "$state/skipped"
    packages=$(var pkgtools/pkg_install PACKAGES)/All
    echo "Building with $workers packages at once, MAKE_JOBS=$make_jobs ($cpus CPUs)"
    stop=0
    trap 'stop=1' TERM INT HUP
    running=0
    changed=1
    while :; do
        for res in "$run"/*.result; do
            [ -f "$res" ] || continue
            set -f
            set -- $(sed -n 1p "$res")
            set +f
            what=$1 path=$2
            shift 2
            case "$what" in
                built) echo "$path $*" >> "$state/done"; echo "$path done" >> "$run/status" ;;
                done) echo "$path done" >> "$run/status" ;;
                skipped) echo "$path $*" >> "$state/skipped"; echo "$path skipped" >> "$run/status" ;;
                *) echo "$path $*" >> "$state/failed"; echo "$path failed" >> "$run/status" ;;
            esac
            rm -f "$res"
            running=$((running - 1))
            changed=1
        done
        if [ "$stop" = 1 ]; then
            [ "$running" -gt 0 ] || { echo 'Stopped; the running packages finished' >&2; trap - TERM INT HUP; rm -rf "$state/build.lock"; return 143; }
        elif [ "$changed" = 1 ] && [ "$running" -lt "$workers" ]; then
            changed=0
            ready $((workers - running)) > "$run/ready"
            while read -r kind path dep; do
                if [ "$kind" = B ]; then
                    echo "$path $dep" >> "$state/blocked"
                    echo "$path blocked" >> "$run/status"
                    changed=1
                else
                    echo "$path running" >> "$run/status"
                    running=$((running + 1))
                    # Without errexit: every package reports a result.
                    (
                        set +e
                        build_one "$path"
                        key=$(echo "$path" | tr / _)
                        [ -f "$run/$key.result" ] || result "$key" "failed $path build"
                    ) < /dev/null > /dev/null 2>&1 &
                fi
            done < "$run/ready"
            [ "$running" -gt 0 ] || [ "$changed" = 1 ] || break
        fi
        [ "$running" -gt 0 ] || [ "$changed" = 1 ] || break
        sleep 1
    done
    trap - TERM INT HUP
    rm -rf "$run" "$state/build.lock"
}

case "$mode" in
    order) order ;;
    fetch) fetch ;;
    build) build ;;
    *) echo "Unknown mode: $mode" >&2; exit 2 ;;
esac

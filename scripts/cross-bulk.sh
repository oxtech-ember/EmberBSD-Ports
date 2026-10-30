#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# Build a list of pkgsrc packages in dependency order with the cross MAKECONF.
#
#   order  Find all dependencies of the list and sort them. Writes STATE/order.
#          List entries the profile skips (PKG_SKIP_REASON) go to
#          STATE/skipped. A graph in which a package reaches a skipped
#          package is refused: no order is written.
#   tools  Add the native nodes (below) to an STATE/order and STATE/edges
#          written before order knew them. Only packages not yet done are
#          asked. Keeps the old files as *.pre-tools-STAMP.
#   fetch  Get the distfiles for STATE/order. Only network and DISTDIR.
#          A package whose distinfo distfiles are all in DISTDIR with
#          their recorded sizes is not queried; the build verifies the
#          checksums.
#   build  Build and install each node of STATE/order, several at once
#          (CROSS_BULK_JOBS, see build below).
#
# The graph has two kinds of nodes. PKGPATH is a target package: its
# DEPENDS and BUILD_DEPENDS are target nodes, its TOOL_DEPENDS and
# BOOTSTRAP_DEPENDS are native nodes PKGPATH@native, built for the native
# host prefix (USE_CROSS_COMPILE=no). Every dependency of a native node is
# native. So the build installs each native tool once, as its own job,
# before the packages that need it, and pkgsrc's depends step finds it.
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
    echo 'Usage: sh scripts/cross-bulk.sh order|tools|fetch|build PKGPATH_LIST ABSOLUTE_STATE' >&2
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
# The queries of the tools mode run as child runs of this script (mode
# deps) and get the verified selection in CROSS_BULK_NATIVE.
unset EMBERBSD_NATIVE_TOOLSET_VERIFIED
if [ "$mode" = deps ] && [ -n "${CROSS_BULK_NATIVE:-}" ]; then
    native=$CROSS_BULK_NATIVE
else
    native=$("$BMAKE" -C "$PKGSRCDIR/pkgtools/pkg_install" show-var \
        VARNAME=EMBERBSD_NATIVE_TOOLSET_VERIFIED < /dev/null) || {
        echo 'The native host prefix selection failed verification' >&2
        exit 2
    }
fi
unset CROSS_BULK_NATIVE
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

# Print the PKG_SKIP_REASON of a node on the first line, then its
# dependency nodes, one per line.
node_deps()
{
    case "$1" in
        *@native) set -- "${1%@native}" @native USE_CROSS_COMPILE=no ;;
        *) set -- "$1" '' ;;
    esac
    dir=$1 suffix=$2
    shift 2
    vars=$(mk -C "$PKGSRCDIR/$dir" "$@" show-vars \
        VARNAMES='PKG_SKIP_REASON DEPENDS BUILD_DEPENDS TOOL_DEPENDS BOOTSTRAP_DEPENDS' < /dev/null) ||
        return 1
    printf '%s\n' "$vars" | sed -n 1p
    printf '%s\n' "$vars" | awk -v suffix="$suffix" '
        NR == 1 { next }
        { s = NR <= 3 ? suffix : "@native"; n = split($0, w, " ")
          for (i = 1; i <= n; i++)
              if (match(w[i], /:\.\.\/\.\.\/[^\/:]+\/[^\/:]+$/)) print substr(w[i], RSTART + 7) s }' |
        sort -u
}

# Print "dependent -> skipped" for each edge in $2 that reaches a node
# listed in $1. A skipped package is outside this profile; nothing may
# depend on it.
skipped_deps()
{
    awk 'FILENAME == ARGV[1] { skip[$1] = 1; next } ($1 in skip) && $1 != $2 { print $2 " -> " $1 }' "$1" "$2"
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
            node_deps "$path" > "$state/deps" 2>> "$state/logs/order.err" || {
                echo "$path $path" >> "$state/edges.new"
                echo "$path order" >> "$state/failed"
                continue
            }
            skip=$(sed -n 1p "$state/deps")
            if [ -n "$skip" ]; then
                echo "$path $skip" >> "$state/skipped.new"
                continue
            fi
            echo "$path $path" >> "$state/edges.new"
            sed 1d "$state/deps" | while read -r dep; do
                [ -n "$dep" ] || continue
                echo "$dep $path" >> "$state/edges.new"
                echo "$dep" >> "$state/next"
            done
        done < "$state/queue"
        sort -u "$state/next" > "$state/queue"
    done
    refused=$(skipped_deps "$state/skipped.new" "$state/edges.new")
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

# tools: the native nodes of an order written before order knew them. The
# queries run CROSS_BULK_JOBS at a time (default: the CPUs) as child runs
# of this script in the deps mode.
tools()
{
    q=$state/tools.d
    jobs=${CROSS_BULK_JOBS:-$(host_cpus)}
    count CROSS_BULK_JOBS "$jobs"
    rm -rf "$q"
    mkdir "$q"
    touch "$state/done" "$state/skipped"
    awk 'FILENAME == ARGV[1] { done[$1] = 1; next } !/@native$/ && !($1 in done)' \
        "$state/done" "$state/order" > "$q/queue"
    cp "$state/edges" "$q/edges"
    : > "$q/seen"
    : > "$q/skipped"
    : > "$q/failed"
    while [ -s "$q/queue" ]; do
        cat "$q/queue" >> "$q/seen"
        CROSS_BULK_NATIVE=$native xargs -P "$jobs" -I '{}' sh "$0" deps '{}' "$q" < "$q/queue"
        : > "$q/next"
        while read -r node; do
            key=$(echo "$node" | tr / _)
            if [ ! -f "$q/$key.deps" ]; then
                echo "$node tools" >> "$q/failed"
                continue
            fi
            skip=$(sed -n 1p "$q/$key.deps")
            case "$node" in
                *@native)
                    if [ -n "$skip" ]; then echo "$node $skip" >> "$q/skipped"; continue; fi
                    echo "$node $node" >> "$q/edges" ;;
            esac
            sed 1d "$q/$key.deps" | while read -r dep; do
                case "$dep" in *@native) ;; *) continue ;; esac
                echo "$dep $node" >> "$q/edges"
                grep -qFx "$dep" "$q/seen" || echo "$dep" >> "$q/next"
            done
        done < "$q/queue"
        sort -u "$q/next" > "$q/queue"
    done
    if [ -s "$q/failed" ]; then
        echo 'Refused: the dependencies of these packages could not be read:' >&2
        cat "$q/failed" >&2
        return 1
    fi
    refused=$(skipped_deps "$q/skipped" "$q/edges")
    if [ -n "$refused" ]; then
        echo 'Refused: these packages depend on packages the profile skips:' >&2
        echo "$refused" >&2
        return 1
    fi
    sort -u "$q/edges" > "$q/edges.sorted"
    tsort "$q/edges.sorted" > "$q/order"
    stamp=$(date '+%Y%m%d%H%M%S')
    cp "$state/order" "$state/order.pre-tools-$stamp"
    cp "$state/edges" "$state/edges.pre-tools-$stamp"
    mv "$q/edges.sorted" "$state/edges"
    mv "$q/order" "$state/order"
    rm -rf "$q"
    echo "Ordered $(wc -l < "$state/order") packages, $(grep -c '@native$' "$state/order") of them native: $state/order"
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
        dir=${path%@native}
        have_distfiles "$dir" && continue
        if [ "$dir" = "$path" ]; then set --; else set -- USE_CROSS_COMPILE=no; fi
        skip=$(mk -C "$PKGSRCDIR/$dir" "$@" show-var VARNAME=PKG_SKIP_REASON < /dev/null) || skip=
        if [ -n "$skip" ]; then
            echo "$path $skip" >> "$state/skipped"
            continue
        fi
        log=$state/logs/fetch-$(echo "$path" | tr / _).log
        mk -C "$PKGSRCDIR/$dir" "$@" fetch < /dev/null > "$log" 2>&1 ||
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

# A node starts only when every dependency node in STATE/edges is done, so
# a package never builds a dependency itself. Only the scheduler writes the
# state files; a node reports its result in STATE/run/KEY.result, written to
# a temporary name and renamed. Compiles never wait for a lock; only the
# installs into a shared prefix do. pkgsrc runs every pkg_add as
# NATIVE_PKG_ADD_CMD, which the build points at STATE/run/pkg_add. That
# wrapper holds a directory lock in STATE/locks per package database (its
# first -K argument: the target sysroot or the native host prefix), so
# installs into one prefix never overlap. mkdir is atomic on macOS, NetBSD
# and Linux alike.
pkg_add_wrapper()
{
    cat <<WRAPPER
#!/bin/sh
# Written by scripts/cross-bulk.sh build: one pkg_add per package database.
db=default
prev=
for arg do
    if [ "\$prev" = -K ]; then db=\$arg; break; fi
    prev=\$arg
done
lock=$state/locks/\$(printf '%s' "\$db" | tr -c 'A-Za-z0-9._-' '_')
until mkdir "\$lock" 2> /dev/null; do sleep 1; done
trap 'rmdir "\$lock"' EXIT
trap 'exit 143' TERM INT HUP
rc=0
$1 "\$@" || rc=\$?
exit "\$rc"
WRAPPER
}

bmk()
{
    if [ "$make_jobs" = makeconf ]; then
        mk NATIVE_PKG_ADD_CMD="$run/pkg_add" "$@"
    else
        mk MAKE_JOBS="$make_jobs" NATIVE_PKG_ADD_CMD="$run/pkg_add" "$@"
    fi
}

result()
{
    printf '%s\n' "$2" > "$run/$1.tmp"
    mv "$run/$1.tmp" "$run/$1.result"
    reported=1
}

# A native node is built and installed into the native host prefix as
# pkgsrc's depends step would do it. One that a target package needs gets
# the target settings (CROSSTARGETSETTINGS) that pkgsrc passes to such a
# tool. It is done when the native prefix has a package of its PKGBASE.
build_native()
{
    nnode=$1 key=$2 path=${1%@native}
    set -f
    set -- USE_CROSS_COMPILE=no
    ! grep -qFx "$nnode" "$run/crossfed" || set -- "$@" $target_settings
    set +f
    vars=$(bmk -C "$PKGSRCDIR/$path" "$@" show-vars VARNAMES='PKGNAME WRKDIR PKG_SKIP_REASON PKGBASE' < /dev/null) ||
        { result "$key" "failed $nnode vars"; return 0; }
    name=$(printf '%s\n' "$vars" | sed -n 1p)
    wrkdir=$(printf '%s\n' "$vars" | sed -n 2p)
    skip=$(printf '%s\n' "$vars" | sed -n 3p)
    base=$(printf '%s\n' "$vars" | sed -n 4p)
    if [ -n "$skip" ]; then
        result "$key" "skipped $nnode $skip"
        return 0
    fi
    installed=
    set -f
    [ -z "$base" ] || ! $native_pkg_info -e "$base" > /dev/null 2>&1 || installed=1
    set +f
    if [ -n "$installed" ]; then
        result "$key" "done $nnode"
        return 0
    fi
    log=$state/logs/$key.log
    echo "$(date '+%Y-%m-%d %H:%M:%S') start $nnode $name" >> "$state/progress"
    case "$wrkdir" in /*) [ ! -d "$wrkdir" ] || chmod -R u+w "$wrkdir" ;; esac
    if bmk -C "$PKGSRCDIR/$path" "$@" clean < /dev/null > "$log" 2>&1 &&
        bmk -C "$PKGSRCDIR/$path" "$@" _AUTOMATIC=yes install < /dev/null >> "$log" 2>&1; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') done $nnode" >> "$state/progress"
        result "$key" "built $nnode $name native"
        return 0
    fi
    echo "$(date '+%Y-%m-%d %H:%M:%S') FAILED $nnode" >> "$state/progress"
    result "$key" "failed $nnode build"
}

build_one()
{
    path=$1
    key=$(echo "$path" | tr / _)
    case "$path" in *@native) build_native "$path" "$key"; return 0 ;; esac
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
            bmk -C "$PKGSRCDIR/$path" depends < /dev/null >> "$log" 2>&1 &&
            bmk -C "$PKGSRCDIR/$path" package < /dev/null >> "$log" 2>&1 &&
            bmk -C "$PKGSRCDIR/$path" package-install < /dev/null >> "$log" 2>&1
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
    rm -rf "$run" "$state/locks" "$state/install.lock"
    mkdir "$run" "$state/locks"
    : > "$run/status"
    real_pkg_add=$(var pkgtools/pkg_install NATIVE_PKG_ADD_CMD)
    [ -n "$real_pkg_add" ] || { echo 'NATIVE_PKG_ADD_CMD is empty' >&2; exit 2; }
    pkg_add_wrapper "$real_pkg_add" > "$run/pkg_add"
    chmod +x "$run/pkg_add"
    native_pkg_info=$(mk -C "$PKGSRCDIR/pkgtools/pkg_install" USE_CROSS_COMPILE=no \
        show-var VARNAME=PKG_INFO < /dev/null)
    target_settings=$(var pkgtools/pkg_install CROSSTARGETSETTINGS)
    # The native nodes that a target package needs as a tool.
    awk '$1 ~ /@native$/ && $2 !~ /@native$/ { print $1 }' "$state/edges" | sort -u > "$run/crossfed"
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
                    # The scheduler may take the result at once, so the
                    # check is a flag, not the file; build_one changes $path.
                    (
                        set +e
                        node=$path
                        reported=
                        build_one "$node"
                        [ -n "$reported" ] || result "$(echo "$node" | tr / _)" "failed $node build"
                    ) < /dev/null > /dev/null 2>&1 &
                fi
            done < "$run/ready"
            [ "$running" -gt 0 ] || [ "$changed" = 1 ] || break
        fi
        [ "$running" -gt 0 ] || [ "$changed" = 1 ] || break
        sleep 1
    done
    trap - TERM INT HUP
    rm -rf "$run" "$state/locks" "$state/build.lock"
}

case "$mode" in
    order) order ;;
    tools) tools ;;
    deps)
        key=$(echo "$list" | tr / _)
        node_deps "$list" > "$state/$key.tmp" 2> "$state/$key.err" &&
            mv "$state/$key.tmp" "$state/$key.deps" ;;
    fetch) fetch ;;
    build) build ;;
    *) echo "Unknown mode: $mode" >&2; exit 2 ;;
esac

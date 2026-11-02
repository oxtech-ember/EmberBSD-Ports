#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# Build a list of pkgsrc packages in dependency order with the cross MAKECONF.
#
#   order  Find all dependencies of the list and sort them. Writes STATE/order.
#          Independent frontier queries use CROSS_BULK_JOBS (default: CPUs).
#          List entries the profile skips (PKG_SKIP_REASON) go to
#          STATE/skipped. A graph in which a package reaches a skipped
#          package is refused: no order is written.
#   fetch  Get the distfiles for STATE/order. Only network and DISTDIR.
#          A package whose distinfo distfiles are all in DISTDIR with
#          their recorded sizes is not queried; the build verifies the
#          checksums.
#   build  Build and install each node of STATE/order, several at once
#          (CROSS_BULK_JOBS, see build below).
#          Independent work drains after a failure. Exit 0 means the pass
#          has no failed or blocked packages; exit 1 means it does.
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
# Each pass checks every done package by its PKGNAME, and a target-mode
# parse costs seconds. Build keeps the show-vars answers in STATE/vars with
# the makefiles that parse read (.MAKE.MAKEFILES) and the device, inode,
# size and modification time of each of them and of their directories. A
# change to any of them, such as a PKGREVISION in an included .mk, an
# edited MAKECONF, a replaced tree or a file added next to a makefile,
# parses again; so does a makefile changed while it was parsed.
# CROSS_BULK_VARS_CACHE=no turns the cache off.
#
# Before a package builds, build renames its old WRKDIR into a trash
# directory on the same file system (WRKOBJDIR/.cross-bulk-trash), so the
# WRKDIR path is free at once and pkgsrc's clean step has nothing left to
# remove. One deleter per build removes the trash in the background, one
# tree at a time and at the lowest priority, and stops with the build; the
# next build removes what a stopped or crashed run left there. Without a
# WRKOBJDIR, or for a WRKDIR on another file system, the clean step removes
# the WRKDIR as before (CROSS_BULK_TRASH=no forces that).
#
# A built package is recorded in STATE/done with its PKGNAME and SHA256.
# The build skips a package whose PKGPATH and PKGNAME have a record there
# and whose package file exists; the file is not hashed again. A new
# PKGNAME or a missing package file builds it again.
# Failures go to STATE/failed. Packages with a failed dependency go to
# STATE/blocked. Logs are in STATE/logs.
set -eu
umask 022

[ "$#" -eq 3 ] || {
    echo 'Usage: sh scripts/cross-bulk.sh order|fetch|build PKGPATH_LIST ABSOLUTE_STATE' >&2
    echo '       sh scripts/cross-bulk.sh package-install PKGPATH ABSOLUTE_STATE' >&2
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
# Parallel order queries run as child runs of this script (mode deps) and
# get the verified selection in CROSS_BULK_NATIVE.
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
if [ "$mode" = deps ] && [ -n "${CROSS_BULK_OPTIONS_CACHE:-}" ]; then
    expected_cache=$(dirname "$state")/build-options
    [ "$CROSS_BULK_OPTIONS_CACHE" = "$expected_cache" ] || {
        echo 'The order query cache is outside its owning state directory' >&2
        exit 2
    }
    cache=$CROSS_BULK_OPTIONS_CACHE
    cachearg=$cache
fi

mk()
{
    "$BMAKE" EMBERBSD_NATIVE_TOOLSET_VERIFIED="$native" \
        ${cachearg:+"PBULK_CACHE_DIRECTORY=$cachearg"} "$@"
}

# pkg-build-options.mk keys cache files by PKGBASE. One graph can contain a
# target package and its native build tool with the same base but different
# installed options, so keep the existing node role in the cache directory.
option_cache_role()
{
    [ -n "$cachearg" ] || return 0
    case "$1" in
        *@native) cachearg=$cache/native ;;
        *) cachearg=$cache/target ;;
    esac
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
        [ -z "$(cd "$PKGSRCDIR" && find mk $(sed 's/@native$//' "$state/order" | sort -u) -newer "$cache/identity" -print | head -n 1)" ]; then
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

# The pkg_info of the native prefix, for the tools it already has.
native_info()
{
    [ -z "${native_pkg_info:-}" ] || return 0
    native_pkg_info=
    [ "$mode" != deps ] || native_pkg_info=${CROSS_BULK_PKG_INFO:-}
    [ -n "$native_pkg_info" ] ||
        native_pkg_info=$(mk -C "$PKGSRCDIR/pkgtools/pkg_install" USE_CROSS_COMPILE=no \
            show-var VARNAME=PKG_INFO < /dev/null)
    [ -n "$native_pkg_info" ] || { echo 'The native PKG_INFO is empty' >&2; exit 2; }
}

# Whether the native prefix has the package base $1 at the version of the
# PKGNAME $2 or newer. pkg_info matches BASE>=VERSION with the version
# order that pkgsrc uses for dependency patterns. A newer installed package
# is current; an older one is not, and its node is built again.
native_current()
{
    [ -n "$1" ] || return 1
    case "$2" in
        "$1"-[0-9]*) set -- "$1>=${2#"$1"-}" ;;
        *) set -- "$1" ;;
    esac
    set -f
    if $native_pkg_info -e "$1" > /dev/null 2>&1; then set +f; return 0; fi
    set +f
    return 1
}

# Print the PKG_SKIP_REASON of a node on the first line, then its
# dependency nodes, one per line. A native node that the native prefix
# already has at its version or newer is a leaf: the build does not build it again, so its own
# tools do not matter. This is what breaks the cycles among the bootstrap
# tools (coreutils and gettext-tools need each other, python needs both).
node_deps()
{
    case "$1" in
        *@native) set -- "${1%@native}" @native USE_CROSS_COMPILE=no ;;
        *) set -- "$1" '' ;;
    esac
    dir=$1 suffix=$2
    shift 2
    option_cache_role "$suffix"
    # The dependencies come from the makefiles alone. A WRKDIR left by an
    # earlier build has the saved MAKEVARS of its phases
    # (WRKDIR/.PHASE_makevars.mk), and a parse includes the latest of them
    # unless _MAKEVARS_MK is defined: a USE_BUILTIN.openssl=yes saved before
    # security/heimdal chose PREFER.openssl=pkgsrc dropped its openssl edge.
    vars=$(mk -C "$PKGSRCDIR/$dir" "$@" _MAKEVARS_MK=defined show-vars \
        VARNAMES='PKG_SKIP_REASON DEPENDS BUILD_DEPENDS TOOL_DEPENDS BOOTSTRAP_DEPENDS PKGBASE PKGNAME' < /dev/null) ||
        return 1
    printf '%s\n' "$vars" | sed -n 1p || return 1
    if [ -n "$suffix" ]; then
        base=$(printf '%s\n' "$vars" | sed -n 6p) || return 1
        name=$(printf '%s\n' "$vars" | sed -n 7p) || return 1
        ! native_current "$base" "$name" || return 0
    fi
    deps=$(printf '%s\n' "$vars" | awk -v suffix="$suffix" '
        NR == 1 || NR > 5 { next }
        { s = NR <= 3 ? suffix : "@native"; n = split($0, w, " ")
          for (i = 1; i <= n; i++)
              if (match(w[i], /:\.\.\/\.\.\/[^\/:]+\/[^\/:]+$/)) print substr(w[i], RSTART + 7) s }') || return 1
    printf '%s\n' "$deps" | sort -u
}

# Print "dependent -> skipped" for each edge in $2 that reaches a node
# listed in $1. A skipped package is outside this profile; nothing may
# depend on it.
skipped_deps()
{
    awk 'FILENAME == ARGV[1] { skip[$1] = 1; next } ($1 in skip) && $1 != $2 { print $2 " -> " $1 }' "$1" "$2"
}

# Sort the edges $1 into $2. A cycle is refused: tsort would still print
# an order, with some package before its dependency.
sort_edges()
{
    tsort "$1" > "$2" 2> "$state/tsort.err" && [ ! -s "$state/tsort.err" ] && return 0
    echo 'Refused: the dependency graph has a cycle:' >&2
    cat "$state/tsort.err" >&2
    rm -f "$2"
    return 1
}

order()
{
    native_info
    new_cache
    jobs=${CROSS_BULK_JOBS:-$(host_cpus)}
    count CROSS_BULK_JOBS "$jobs"
    q=$state/order-query
    rm -rf "$q"
    mkdir "$q"
    : > "$q/failed"
    : > "$state/edges.new"
    : > "$state/skipped.new"
    sort -u "$list" > "$state/queue"
    : > "$state/seen"
    query_index=0
    while [ -s "$state/queue" ]; do
        : > "$state/next"
        : > "$q/frontier"
        : > "$q/frontier-map"
        awk 'function trim(s) {
                 sub(/^[ \t]+/, "", s)
                 sub(/[ \t]+$/, "", s)
                 return s
             }
             FILENAME == ARGV[1] { seen[trim($0)] = 1; next }
             { path = trim($0) }
             !(path in seen) { seen[path] = 1; print path }' \
            "$state/seen" "$state/queue" > "$state/queue.filtered"
        cat "$state/queue.filtered" >> "$state/seen"
        mv "$state/queue.filtered" "$state/queue"
        while read -r path; do
            key=node-$query_index
            query_index=$((query_index + 1))
            printf '%s|%s\n' "$key" "$path" >> "$q/frontier"
            printf '%s %s\n' "$path" "$key" >> "$q/frontier-map"
        done < "$state/queue"
        if [ -s "$q/frontier" ]; then
            CROSS_BULK_NATIVE=$native CROSS_BULK_PKG_INFO=$native_pkg_info \
                CROSS_BULK_OPTIONS_CACHE=$cache \
                xargs -P "$jobs" -I '{}' sh "$0" deps '{}' "$q" \
                < "$q/frontier" || :
        fi
        while read -r path key; do
            cat "$q/$key.err" >> "$state/logs/order.err" 2>/dev/null || :
            if [ ! -f "$q/$key.deps" ]; then
                echo "$path $key" >> "$q/failed"
                echo "$path order" >> "$state/failed"
                continue
            fi
            skip=$(sed -n 1p "$q/$key.deps")
            if [ -n "$skip" ]; then
                echo "$path $skip" >> "$state/skipped.new"
                continue
            fi
            echo "$path $path" >> "$state/edges.new"
            sed 1d "$q/$key.deps" | while read -r dep; do
                [ -n "$dep" ] || continue
                echo "$dep $path" >> "$state/edges.new"
                echo "$dep" >> "$state/next"
            done
        done < "$q/frontier-map"
        if [ -s "$q/failed" ]; then
            echo 'Refused: the dependencies of these packages could not be read:' >&2
            while read -r path key; do
                echo "$path order" >&2
                [ ! -s "$q/$key.err" ] || tail -n 5 "$q/$key.err" | sed 's/^/    /' >&2
            done < "$q/failed"
            return 1
        fi
        sort -u "$state/next" > "$state/queue"
    done
    refused=$(skipped_deps "$state/skipped.new" "$state/edges.new")
    if [ -n "$refused" ]; then
        echo 'Refused: these packages depend on packages the profile skips:' >&2
        echo "$refused" >&2
        return 1
    fi
    sort_edges "$state/edges.new" "$state/order.new" || return 1
    mv "$state/skipped.new" "$state/skipped"
    mv "$state/edges.new" "$state/edges"
    mv "$state/order.new" "$state/order"
    rm -f "$state/queue" "$state/next"
    rm -rf "$q"
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
    # A native tool that a target package needs gets the target settings,
    # as in build (build_native): cross-libtool refuses to parse without them.
    target_settings=$(var pkgtools/pkg_install CROSSTARGETSETTINGS)
    crossfed=$(awk '$1 ~ /@native$/ && $2 !~ /@native$/ { print $1 }' "$state/edges" | sort -u)
    while read -r path; do
        dir=${path%@native}
        have_distfiles "$dir" && continue
        set -f
        if [ "$dir" = "$path" ]; then set --
        elif printf '%s\n' "$crossfed" | grep -qFx "$path"; then set -- USE_CROSS_COMPILE=no $target_settings
        else set -- USE_CROSS_COMPILE=no; fi
        set +f
        option_cache_role "$path"
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
# half the host CPUs). Each gets MAKE_JOBS on the command line (default: 1.5 x
# CPUs split over the packages, at most the CPUs), which also reaches pkgsrc's
# dependency recursion; MAKE_JOBS_SAFE=no recipes stay serial. Set
# CROSS_BULK_MAKE_JOBS to a positive integer for an explicit override.
# CROSS_BULK_CPUS overrides the SDK's detected CPU count.
host_cpus()
{
    set --
    [ -z "${CROSS_BULK_CPUS:-}" ] || set -- --jobs "$CROSS_BULK_CPUS"
    selected=$(mk -C "$PKGSRCDIR/pkgtools/pkg_install" \
        show-vars VARNAMES='EMBERBSD_HOST_PYTHON EMBERBSD_SDK_SOURCE' < /dev/null) || {
        echo 'Cannot read the selected SDK source and host Python from MAKECONF' >&2
        exit 2
    }
    [ "$(printf '%s\n' "$selected" | wc -l | tr -d ' ')" = 2 ] || {
        echo 'Unexpected selected SDK source and host Python metadata' >&2
        exit 2
    }
    host_python=$(printf '%s\n' "$selected" | sed -n 1p)
    sdk_source=$(printf '%s\n' "$selected" | sed -n 2p)
    case "$host_python" in /*) ;; *) echo 'EMBERBSD_HOST_PYTHON is not an absolute selected tool path' >&2; exit 2 ;; esac
    case "$sdk_source" in /*) ;; *) echo 'EMBERBSD_SDK_SOURCE is not an absolute SDK source path' >&2; exit 2 ;; esac
    n=$("$host_python" -B -E -S "$sdk_source/scripts/resolve-jobs.py" "$@") || {
        echo 'The SDK could not resolve the available CPU count' >&2
        exit 2
    }
    count SDK_CPU_COUNT "$n"
    echo "$n"
}

count()
{
    case "$2" in ''|*[!0-9]*|0) echo "$1 must be a positive number: $2" >&2; exit 2 ;; esac
}

# A node starts only when every dependency node in STATE/edges is done, so
# a package never builds a dependency itself. pkgsrc's depends step would
# still build one in place (DEPENDS_TARGET in the dependency's directory and
# WRKDIR) when the installed package does not match the required pattern,
# such as a buildlink pin older than the built PKGREVISION; two dependents
# would then build in one WRKDIR at once. So every build run gets a
# DEPENDS_TARGET that no makefile defines: such a dependent fails at once,
# and its log names the dependency ("Verifying
# emberbsd-refuse-unpreflighted-dependency for ...").
# Only the scheduler writes the
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

dev_of()
{
    stat -c %d "$1" 2> /dev/null || stat -f %d "$1" 2> /dev/null
}

# The trash directory: WRKOBJDIR/.cross-bulk-trash, or none.
trash_init()
{
    trash=
    [ "${CROSS_BULK_TRASH:-yes}" != no ] || return 0
    wrkobj=$(var pkgtools/pkg_install WRKOBJDIR)
    case "$wrkobj" in /?*) ;; *) return 0 ;; esac
    mkdir -p "$wrkobj/.cross-bulk-trash" 2> /dev/null || return 0
    trash=$(CDPATH= cd -- "$wrkobj/.cross-bulk-trash" && pwd -P) || trash=
    case "$trash" in */.cross-bulk-trash) ;; *) trash= ; return 0 ;; esac
    trash_dev=$(dev_of "$trash") || trash=
}

# Rename an old WRKDIR ($1) of job $2 into the trash: one rename on the
# same file system. Fails (and the clean step removes it) when there is
# no trash or the WRKDIR is on another file system.
retire()
{
    [ -n "$trash" ] || return 1
    case "$1" in /?*) ;; *) return 1 ;; esac
    [ -d "$1" ] && [ ! -L "$1" ] || return 0
    [ "$(dev_of "$(dirname "$1")")" = "$trash_dev" ] || return 1
    mv "$1" "$trash/$stamp.$2" 2> /dev/null && [ ! -e "$1" ]
}

# Set clean to the clean target, or to nothing when the WRKDIR ($1) went to
# the trash: each target-mode bmake run parses the whole package again
# (seconds each), and the clean step would have nothing to remove.
prepare_wrkdir()
{
    clean=clean
    if retire "$1" "$2"; then
        [ -e "$1" ] || [ -L "$1" ] || clean=
    else
        # Make it removable for the clean step: Go module caches are read-only.
        case "$1" in /*) [ ! -d "$1" ] || chmod -R u+w "$1" ;; esac
    fi
}

# Retire successful workdirs only when the caller opts in. If a rename to the
# same-filesystem trash is unavailable, use pkgsrc's scoped clean target.
# Cleanup trouble is diagnostic; it must not undo a completed installation.
clean_success()
{
    [ "${CROSS_BULK_CLEAN_SUCCESS:-no}" = yes ] || return 0
    if retire "$wrkdir" "$job.$key.complete" &&
        [ ! -e "$wrkdir" ] && [ ! -L "$wrkdir" ]; then
        return 0
    fi
    if ! bmk -C "$PKGSRCDIR/$path" "$@" clean < /dev/null >> "$log" 2>&1; then
        echo "WARNING: $node built successfully but WRKDIR cleanup failed: $wrkdir" >&2
        echo "WARNING: $node built successfully but WRKDIR cleanup failed: $wrkdir" >> "$log"
    fi
    return 0
}

# Remove the entries of the trash one at a time at the lowest priority,
# without following symbolic links, until the build ($1) is gone. Only
# this directory's own entries are removed.
deleter()
{
    set +e
    lowprio='nice -n 19'
    if [ -x /usr/sbin/taskpolicy ]; then
        lowprio="/usr/sbin/taskpolicy -b $lowprio"
    elif command -v ionice > /dev/null 2>&1; then
        lowprio="ionice -c 3 $lowprio"
    fi
    while kill -0 "$1" 2> /dev/null; do
        busy=
        for entry in "$trash"/* "$trash"/.[!.]*; do
            [ -e "$entry" ] || [ -L "$entry" ] || continue
            case "${entry#"$trash"/}" in ''|*/*) continue ;; esac
            if [ -d "$entry" ] && [ ! -L "$entry" ]; then
                $lowprio chmod -R u+w "$entry" 2> /dev/null || :
                $lowprio rm -rf "$entry" 2> /dev/null || :
            else
                rm -f "$entry" 2> /dev/null || :
            fi
            busy=1
            kill -0 "$1" 2> /dev/null || return 0
        done
        [ -n "$busy" ] || sleep 2
    done
}

# Heavy links. CROSS_BULK_LINK_LAUNCHER is the SDK heavy-link launcher
# prefix, as in the bootstrap mk.conf: "PYTHON SDK/scripts/link-launcher.py
# --lock-root LOCKS --context CONTEXT --", absolute words without spaces.
# Every build make gets it as EMBERBSD_DARWIN_LINKER_LAUNCHER and
# EMBERBSD_GCC16_LINKER_LAUNCHER, and as the CMake list
# EMBERBSD_DARWIN_CMAKE_LINKER_LAUNCHER, so the recipes that honour them
# link one heavy group at a time across all CROSS_BULK_JOBS packages and
# every other build that shares CONTEXT. Unset: no launcher, as before.
link_args= link_list=
link_launcher_args()
{
    link_args=
    [ -n "${CROSS_BULK_LINK_LAUNCHER:-}" ] || return 0
    set -f
    set -- $CROSS_BULK_LINK_LAUNCHER
    set +f
    case "$1" in /*) ;; *) echo "CROSS_BULK_LINK_LAUNCHER must start with an absolute path" >&2; exit 2 ;; esac
    eval "last=\${$#}"
    [ "$last" = -- ] || { echo "CROSS_BULK_LINK_LAUNCHER must end with --" >&2; exit 2; }
    link_list=$(printf '%s;' "$@"); link_list=${link_list%;}
    link_args=yes
}

# Build runs: see the DEPENDS_TARGET note above.
bmk()
{
    if [ -n "$link_args" ]; then
        set -- EMBERBSD_DARWIN_LINKER_LAUNCHER="$CROSS_BULK_LINK_LAUNCHER" \
            EMBERBSD_GCC16_LINKER_LAUNCHER="$CROSS_BULK_LINK_LAUNCHER" \
            EMBERBSD_DARWIN_CMAKE_LINKER_LAUNCHER="$link_list" "$@"
    fi
    mk MAKE_JOBS="$make_jobs" NATIVE_PKG_ADD_CMD="$run/pkg_add" \
        DEPENDS_TARGET=emberbsd-refuse-unpreflighted-dependency "$@"
}

# Print device, inode, size, modification time and name of each path.
sigs()
{
    if [ "$gnu_stat" = yes ]; then
        stat -c '%d %i %s %.9Y %n' "$@" 2> /dev/null || :
    else
        stat -f '%d %i %z %Fm %N' "$@" 2> /dev/null || :
    fi
}

# The signatures of the makefiles $2 that a parse in package directory $1
# read, and of their directories.
makefile_sigs()
{
    (
        cd "$PKGSRCDIR/$1" || exit 0
        set -f
        set -- $(printf '%s\n' $2 | awk '{ print; d = $0
            if (!sub("/[^/]*$", "", d)) d = "."
            if (d == "") d = "/"
            print d }' | sort -u)
        sigs "$@"
    )
}

# The values of the variables $2 of package directory $1, one per line, as
# show-vars prints them; further arguments go to bmake. See STATE/vars above.
pkg_vars()
{
    vdir=$1 vnames=$2
    shift 2
    ventry=
    if [ -n "$vars_cache" ]; then
        ventry=$vars_cache/$(printf '%s\n' "$vdir $vnames $*" | cksum | tr ' ' _)
        if [ -f "$ventry" ] && [ -f "$ventry.sig" ] &&
            makefile_sigs "$vdir" "$(sed -n 1p "$ventry")" | cmp -s - "$ventry.sig"; then
            sed 1d "$ventry"
            return 0
        fi
        : > "$ventry.start"
    fi
    vout=$(bmk -C "$PKGSRCDIR/$vdir" "$@" show-vars VARNAMES="$vnames .MAKE.MAKEFILES .CURDIR" < /dev/null) ||
        return 1
    vn=$(set -f; set -- $vnames; echo $#)
    if [ "$(printf '%s\n' "$vout" | wc -l | tr -d ' ')" != $((vn + 2)) ]; then
        # Not one line per variable: use it as it is, keep nothing.
        printf '%s\n' "$vout"
        return 0
    fi
    printf '%s\n' "$vout" | sed -n "1,${vn}p"
    vfiles=$(printf '%s\n' "$vout" | sed -n "$((vn + 1))p")
    [ -n "$ventry" ] && [ -n "$vfiles" ] || return 0
    # A makefile changed during the parse may not be what it read.
    (
        cd "$PKGSRCDIR/$vdir" || exit 1
        set -f
        [ -z "$(find $vfiles -prune -newer "$ventry.start" 2> /dev/null)" ]
    ) || return 0
    makefile_sigs "$vdir" "$vfiles" > "$ventry.sig.tmp" &&
        { printf '%s\n' "$vfiles"; printf '%s\n' "$vout" | sed -n "1,${vn}p"; } > "$ventry.tmp" &&
        mv "$ventry.sig.tmp" "$ventry.sig" && mv "$ventry.tmp" "$ventry" || :
}

result()
{
    printf '%s\n' "$2" > "$run/$1.tmp"
    mv "$run/$1.tmp" "$run/$1.result"
    reported=1
}

# A native node is built and installed into the native host prefix as
# pkgsrc's depends step would do it. Its binary package goes to
# PACKAGES-native/All, not to PACKAGES/All, where the target package of
# the same PKGNAME is and where STATE/done has its record. One that a
# target package needs gets the target settings (CROSSTARGETSETTINGS)
# that pkgsrc passes to such a tool. It is done when the native prefix has
# a package of its PKGBASE at its version or newer. An older one is
# replaced (pkgsrc replace, pkg_add -U), which keeps the packages that
# depend on it registered. The replace runs alone (see exclusive).
build_native()
{
    nnode=$1 key=$2 path=${1%@native}
    set -f
    set -- USE_CROSS_COMPILE=no PACKAGES="$native_packages"
    ! grep -qFx "$nnode" "$run/crossfed" || set -- "$@" $target_settings
    set +f
    vars=$(pkg_vars "$path" 'PKGNAME WRKDIR PKG_SKIP_REASON PKGBASE' "$@") ||
        { result "$key" "failed $nnode vars"; return 0; }
    name=$(printf '%s\n' "$vars" | sed -n 1p)
    wrkdir=$(printf '%s\n' "$vars" | sed -n 2p)
    skip=$(printf '%s\n' "$vars" | sed -n 3p)
    base=$(printf '%s\n' "$vars" | sed -n 4p)
    if [ -n "$skip" ]; then
        result "$key" "skipped $nnode $skip"
        return 0
    fi
    if native_current "$base" "$name"; then
        result "$key" "done $nnode"
        return 0
    fi
    install=install why=build
    set -f
    [ -z "$base" ] || ! $native_pkg_info -e "$base" > /dev/null 2>&1 || install=replace
    set +f
    log=$state/logs/$key.log
    echo "$(date '+%Y-%m-%d %H:%M:%S') start $nnode $name" >> "$state/progress"
    prepare_wrkdir "$wrkdir" "$job.$key"
    : > "$log"
    if { [ -z "$clean" ] || bmk -C "$PKGSRCDIR/$path" "$@" clean < /dev/null >> "$log" 2>&1; } &&
        if [ "$install" = replace ]; then
            bmk -C "$PKGSRCDIR/$path" "$@" _AUTOMATIC=yes package < /dev/null >> "$log" 2>&1 &&
                { native_replace_keeps_libraries "$base" "$native_packages/All/$name" >> "$log" 2>&1 ||
                    { why=replace; false; }; } &&
                exclusive "$key" bmk -C "$PKGSRCDIR/$path" "$@" _AUTOMATIC=yes replace < /dev/null >> "$log" 2>&1
        else
            bmk -C "$PKGSRCDIR/$path" "$@" _AUTOMATIC=yes install < /dev/null >> "$log" 2>&1
        fi; then
        clean_success "$@"
        echo "$(date '+%Y-%m-%d %H:%M:%S') done $nnode" >> "$state/progress"
        result "$key" "built $nnode $name native"
        return 0
    fi
    echo "$(date '+%Y-%m-%d %H:%M:%S') FAILED $nnode" >> "$state/progress"
    result "$key" "failed $nnode $why"
}

# Whether replacing the installed native package $1 with the binary package
# $2 (a PKGNAME under PACKAGES-native/All, without its suffix) keeps every
# shared library that it provides now. pkgsrc replace (pkg_add -U) removes
# the files of the installed package mid-pass. A new major version that
# no longer has a library (OpenSSL 4 has libssl.4, not libssl.3) leaves the
# packages that depend on it loading a missing library: the native
# pkg_install among them, and with it every later build in the native
# prefix. Such an update needs its dependents rebuilt with it, between
# passes, so the build refuses the replace, names what it would break and
# keeps the package in PACKAGES-native/All. The PROVIDES and REQUIRES
# lines of the build information list the shared libraries.
native_replace_keeps_libraries()
{
    nr_file=
    for nr_f in "$2".t*; do [ -f "$nr_f" ] && { nr_file=$nr_f; break; }; done
    nr_old=$($native_pkg_info -q -Q PROVIDES "$1" 2> /dev/null) || nr_old=
    [ -n "$nr_old" ] || return 0
    nr_new=
    [ -z "$nr_file" ] || nr_new=$($native_pkg_info -q -Q PROVIDES "$nr_file" 2> /dev/null) || nr_new=
    nr_gone=$(printf '%s\n' "$nr_old" | NR_NEW="$nr_new" awk '
        BEGIN { n = split(ENVIRON["NR_NEW"], w, "\n"); for (i = 1; i <= n; i++) have[w[i]] = 1 }
        $0 != "" && !($0 in have)')
    [ -n "$nr_gone" ] || return 0
    nr_deps=$($native_pkg_info -q -R "$1" 2> /dev/null | awk 'NF') || nr_deps=
    [ -n "$nr_deps" ] || return 0
    echo "Refusing to replace $1 in the native prefix during a pass: ${nr_file:-$2} no longer provides"
    printf '    %s\n' $nr_gone
    echo "and these installed packages depend on $1:"
    for nr_d in $nr_deps; do
        nr_req=$($native_pkg_info -q -Q REQUIRES "$nr_d" 2> /dev/null | NR_GONE="$nr_gone" awk '
            BEGIN { n = split(ENVIRON["NR_GONE"], w, "\n"); for (i = 1; i <= n; i++) gone[w[i]] = 1 }
            $0 in gone' | tr '\n' ' ')
        echo "    $nr_d${nr_req:+ (loads $nr_req)}"
    done
    echo "Install the package and rebuild these between passes."
    return 1
}

# pkgsrc replace (pkg_add -U) deletes the files of the installed package
# before it adds those of the new one. A build that runs at that time in
# the same prefix or sysroot misses them: a tool linked with libffi from
# the native prefix fails with "Library not loaded" while libffi@native is
# replaced. A job therefore builds its package first and runs the replace,
# "$2"..., only when no other job runs: it asks with RUN/$1.replace and
# waits for RUN/$1.replacing, which build gives it when every running job
# waits so; build starts no job while one waits or replaces.
exclusive()
{
    xkey=$1
    shift
    : > "$run/$xkey.replace"
    until [ -f "$run/$xkey.replacing" ]; do sleep 1; done
    xrc=0
    "$@" || xrc=$?
    rm -f "$run/$xkey.replacing"
    return "$xrc"
}

# Run the install targets $2... of target package $1, one bmake run each.
target_install()
{
    tpath=$1
    shift
    shared_arg=
    shared_pair_for_path "$tpath" || :
    if [ -n "$shared_pair" ] && [ "$(cat "$run/shared-$shared_pair/enabled" 2>/dev/null)" = yes ]; then
        shared_stage=$(cat "$run/shared-$shared_pair/stage")
        shared_var=$(cat "$run/shared-$shared_pair/variable")
        if [ "$tpath" = "$shared_producer" ] ||
            { [ -f "$run/shared-$shared_pair/producer-ready" ] && [ -d "$shared_stage" ]; }; then
            shared_arg=$shared_var=$shared_stage
        fi
    fi
    for target do
        if [ -n "$shared_arg" ]; then
            bmk -C "$PKGSRCDIR/$tpath" "$shared_arg" "$target" < /dev/null || return 1
        else
            bmk -C "$PKGSRCDIR/$tpath" "$target" < /dev/null || return 1
        fi
    done
}

# A split package pair can share one compiled payload when the run contains
# both roles and their expanded source, toolchain and build inputs agree.
# Pair-specific data is kept here; staging and lifecycle are shared below.
shared_pair_for_path()
{
    case "$1" in
        lang/llvm|lang/llvm-devel) shared_pair=llvm ;;
        x11/qt6-qtbase|x11/qt6-qtbase-devel) shared_pair=qtbase ;;
        *) shared_pair= ;;
    esac
    [ -z "$shared_pair" ] || shared_pair_config "$shared_pair"
}

shared_pair_config()
{
    pair_key=$1
    shared_pair=$pair_key
    shared_producer=
    shared_consumer=
    shared_variable=
    shared_stage_name=
    shared_fields=
    case "$pair_key" in
        llvm)
            shared_producer=lang/llvm
            shared_consumer=lang/llvm-devel
            shared_variable=EMBERBSD_LLVM_SHARED_STAGE
            shared_stage_name=.llvm-shared-full-stage
            shared_fields='LLVM_VERSION WRKSRC DISTNAME PATCHDIR DISTINFO_FILE PKG_OPTIONS USE_CROSS_COMPILE OPSYS OS_VERSION MACHINE_ARCH MACHINE_GNU_PLATFORM EMBERBSD_CROSS_COMPILER_FAMILY PKGSRC_COMPILER CMAKE CFLAGS CXXFLAGS CPPFLAGS LDFLAGS CMAKE_CONFIGURE_ARGS CONFIGURE_ENV CC CXX CPP AR AS LD RANLIB STRIP CWRAPPERS_APPEND.cc CWRAPPERS_APPEND.cxx _CMAKE_BUILD_SYSTEM INSTALL_TARGET CMAKE_INSTALL_ARGS LLVM_TARGETS_TO_BUILD LLVM_EXPERIMENTAL_TARGETS_TO_BUILD CROSS_DESTDIR TOOLDIR TOOL_PYTHONBIN EMBERBSD_LLVM_NATIVE_TOOLS MAKE_ENV CMAKE_BUILD_ARGS _CMAKE_BUILD_TOOL CMAKE_GENERATOR CMAKE_BUILD_DIR BUILD_TARGET BUILD_DIRS CONFIGURE_DIR SETENV RUN INSTALL_ENV INSTALL_DIRS PREFIX' ;;
        qtbase)
            shared_producer=x11/qt6-qtbase
            shared_consumer=x11/qt6-qtbase-devel
            shared_variable=EMBERBSD_QTBASE_SHARED_STAGE
            shared_stage_name=.qtbase-shared-full-stage
            shared_fields='QTVERSION WRKSRC DISTNAME PATCHDIR DISTINFO_FILE FILESDIR PKG_OPTIONS USE_CROSS_COMPILE OPSYS OS_VERSION MACHINE_ARCH MACHINE_GNU_PLATFORM EMBERBSD_CROSS_COMPILER_FAMILY PKGSRC_COMPILER CMAKE CFLAGS CXXFLAGS CPPFLAGS LDFLAGS CMAKE_CONFIGURE_ARGS CONFIGURE_ARGS CONFIGURE_ENV CC CXX CPP AR AS LD RANLIB STRIP CWRAPPERS_APPEND.cc CWRAPPERS_APPEND.cxx _CMAKE_BUILD_SYSTEM INSTALL_TARGET CMAKE_INSTALL_ARGS CROSS_DESTDIR TOOLDIR TOOL_PYTHONBIN EMBERBSD_NATIVE_TOOLSET_MAKECONF EMBERBSD_WAYLAND_SCANNER MAKE_ENV CMAKE_BUILD_ARGS _CMAKE_BUILD_TOOL CMAKE_GENERATOR CMAKE_BUILD_DIR BUILD_TARGET BUILD_DIRS CONFIGURE_DIR SETENV RUN INSTALL_ENV INSTALL_DIRS PREFIX QTPREFIX' ;;
    esac
}

shared_pair_configure_one()
{
    shared_pair_config "$1"
    shared_dir=$run/shared-$shared_pair
    mkdir -p "$shared_dir"
    printf '%s\n' no > "$shared_dir/enabled"
    printf '%s\n' "$shared_variable" > "$shared_dir/variable"
    grep -qFx "$shared_producer" "$state/order" && grep -qFx "$shared_consumer" "$state/order" || return 0
    shared_runtime_wrkdir=$(pkg_vars "$shared_producer" WRKDIR _MAKEVARS_MK=defined) || {
        echo "$shared_pair producer inputs could not be queried; using ordinary package builds" >&2
        return 0
    }
    case "$shared_runtime_wrkdir" in /*) ;; *)
        echo "$shared_pair producer WRKDIR is not absolute; using ordinary package builds" >&2
        return 0 ;;
    esac
    shared_runtime_values=$(pkg_vars "$shared_producer" "$shared_fields" "WRKDIR=$shared_runtime_wrkdir" _MAKEVARS_MK=defined) || {
        echo "$shared_pair producer compile inputs could not be queried; using ordinary package builds" >&2
        return 0
    }
    shared_devel_values=$(pkg_vars "$shared_consumer" "$shared_fields" "WRKDIR=$shared_runtime_wrkdir" _MAKEVARS_MK=defined) || {
        echo "$shared_pair consumer compile inputs could not be queried; using ordinary package builds" >&2
        return 0
    }
    set -f
    set -- $shared_fields
    shared_expected=$#
    set +f
    if [ "$(printf '%s\n' "$shared_runtime_values" | wc -l | tr -d ' ')" != "$shared_expected" ] ||
        [ "$(printf '%s\n' "$shared_devel_values" | wc -l | tr -d ' ')" != "$shared_expected" ]; then
        echo "$shared_pair compile inputs are incomplete; using ordinary package builds" >&2
        return 0
    fi
    [ "$shared_runtime_values" = "$shared_devel_values" ] || {
        echo "$shared_pair producer and consumer compile inputs differ; using ordinary package builds" >&2
        return 0
    }
    shared_stage=$shared_runtime_wrkdir/$shared_stage_name
    printf '%s\n' "$shared_stage" > "$shared_dir/stage"
    printf '%s\n' "$shared_runtime_wrkdir" > "$shared_dir/wrkdir"
    printf '%s\n' "$shared_producer" > "$shared_dir/producer"
    printf '%s\n' "$shared_consumer" > "$shared_dir/consumer"
    printf '%s\n' yes > "$shared_dir/enabled"
    echo "$shared_pair producer and consumer compile inputs match; enabling same-run stage handoff"
}

shared_pairs_configure()
{
    [ "${CROSS_BULK_SHARED_BUILD:-yes}" = yes ] || return 0
    shared_pair_configure_one llvm
    shared_pair_configure_one qtbase
}

shared_pair_ready()
{
    shared_pair_for_path "$1"
    [ -n "$shared_pair" ] && [ "$(cat "$run/shared-$shared_pair/enabled" 2>/dev/null)" = yes ] &&
        [ -f "$run/shared-$shared_pair/producer-ready" ] &&
        [ -d "$(cat "$run/shared-$shared_pair/stage")" ]
}

shared_pair_producer_succeeded()
{
    shared_pair_for_path "$1"
    [ -n "$shared_pair" ] && [ "$1" = "$shared_producer" ] || return 0
    shared_dir=$run/shared-$shared_pair
    shared_stage=$(cat "$shared_dir/stage")
    if [ -d "$shared_stage" ]; then
        : > "$shared_dir/producer-ready.tmp"
        mv "$shared_dir/producer-ready.tmp" "$shared_dir/producer-ready"
        echo "$shared_pair complete stage retained at $shared_stage"
    else
        echo "$shared_pair producer completed without a complete stage; consumer will build normally"
    fi
}

shared_pair_retire_producer()
{
    shared_pair_for_path "$1"
    [ -n "$shared_pair" ] && [ "$1" = "$shared_consumer" ] || return 0
    shared_dir=$run/shared-$shared_pair
    [ "$(cat "$shared_dir/enabled" 2>/dev/null)" = yes ] && [ -f "$shared_dir/producer-ready" ] || return 0
    [ "${CROSS_BULK_CLEAN_SUCCESS:-no}" = yes ] || return 0
    shared_wrkdir=$(cat "$shared_dir/wrkdir")
    if retire "$shared_wrkdir" "$job.$shared_pair-after-consumer" &&
        [ ! -e "$shared_wrkdir" ] && [ ! -L "$shared_wrkdir" ]; then
        return 0
    fi
    shared_variable=$(cat "$shared_dir/variable")
    if ! bmk -C "$PKGSRCDIR/$shared_producer" "WRKDIR=$shared_wrkdir" \
        "$shared_variable=$(cat "$shared_dir/stage")" clean < /dev/null >> "$log" 2>&1; then
        echo "WARNING: $node built successfully but $shared_pair producer WRKDIR cleanup failed: $shared_wrkdir" >&2
        echo "WARNING: $node built successfully but $shared_pair producer WRKDIR cleanup failed: $shared_wrkdir" >> "$log"
    fi
    return 0
}

shared_pair_reset_stage()
{
    shared_pair_for_path "$1"
    [ "${stage_local:-no}" = yes ] && [ -n "$shared_pair" ] || return 0
    [ "$(cat "$run/shared-$shared_pair/enabled" 2>/dev/null)" = yes ] || return 0
    bmk -C "$PKGSRCDIR/$1" _package-clean < /dev/null || return 1
    if [ "$1" = "$shared_producer" ]; then
        shared_dir=$run/shared-$shared_pair
        shared_stage=$(cat "$shared_dir/stage")
        shared_wrkdir=$(cat "$shared_dir/wrkdir")
        [ "$shared_stage" = "$shared_wrkdir/$shared_stage_name" ] || return 1
        if [ -L "$shared_stage" ]; then
            echo "Refusing symlinked $shared_pair producer stage: $shared_stage" >&2
            return 1
        fi
        if [ -e "$shared_stage" ]; then
            [ -d "$shared_stage" ] || return 1
            rm -r "$shared_stage" || return 1
        fi
    fi
}

build_one()
{
    path=$1
    key=$(echo "$path" | tr / _)
    case "$path" in *@native) build_native "$path" "$key"; return 0 ;; esac
    log=$state/logs/$key.log
    vars=$(pkg_vars "$path" 'PKGNAME WRKDIR PKG_SKIP_REASON PKGBASE') ||
        { result "$key" "failed $path vars"; return 0; }
    name=$(printf '%s\n' "$vars" | sed -n 1p)
    wrkdir=$(printf '%s\n' "$vars" | sed -n 2p)
    skip=$(printf '%s\n' "$vars" | sed -n 3p)
    base=$(printf '%s\n' "$vars" | sed -n 4p)
    if [ -n "$skip" ]; then
        result "$key" "skipped $path $skip"
        return 0
    fi
    file=$packages/$name.tgz
    if [ "${stage_local:-no}" != yes ] && [ -f "$file" ] &&
        awk -v p="$path" -v n="$name" '$1 == p && $2 == n { f = 1; exit } END { exit !f }' "$state/done"; then
        shared_pair_retire_producer "$path"
        result "$key" "done $path"
        return 0
    fi
    # One short line per append: O_APPEND keeps concurrent lines whole.
    echo "$(date '+%Y-%m-%d %H:%M:%S') start $path $name" >> "$state/progress"
    if [ "${stage_local:-no}" != yes ]; then
        prepare_wrkdir "$wrkdir" "$job.$key"
    fi
    : > "$log"
    # One package-install run does depends, package and the install: each
    # target-mode bmake run parses the package again, and the pkg_add wrapper
    # already keeps installs into one database apart. The sysroot may
    # already have another version of the package, such as one from an
    # earlier pass before a PKGREVISION bump; pkg_add refuses to install
    # over it, so the package is built and then replaced (pkgsrc replace,
    # pkg_add -U), which keeps the packages that depend on it registered.
    # The replace runs alone (see exclusive).
    install=package-install
    replace=
    set -f
    [ -z "$base" ] || ! $target_pkg_info -e "$base" > /dev/null 2>&1 || { install=package; replace=replace; }
    set +f
    { [ "${stage_local:-no}" = yes ] || [ -z "$clean" ] || bmk -C "$PKGSRCDIR/$path" clean < /dev/null >> "$log" 2>&1; } &&
        target_install "$path" $install >> "$log" 2>&1 &&
        { [ -z "$replace" ] || if [ "${stage_local:-no}" = yes ]; then
            target_install "$path" replace >> "$log" 2>&1
        else
            exclusive "$key" target_install "$path" replace >> "$log" 2>&1
        fi; } && {
        shared_pair_producer_succeeded "$path"
        if ! shared_pair_ready "$path"; then
            [ "${stage_local:-no}" = yes ] || clean_success
        fi
        shared_pair_retire_producer "$path"
        echo "$(date '+%Y-%m-%d %H:%M:%S') done $path" >> "$state/progress"
        result "$key" "built $path $name $(shasum -a 256 "$file" | cut -d ' ' -f 1)"
        return 0
    }
    echo "$(date '+%Y-%m-%d %H:%M:%S') FAILED $path" >> "$state/progress"
    result "$key" "failed $path build"
}

# Install one explicitly selected package from its existing WRKDIR. This is
# an owner-directed recovery path, not archive reuse: it runs the same
# package-install/package+replace targets as build_one, while preserving the
# workdir and updating only this PKGPATH in the controller state.
state_path_row()
{
    spr_file=$1 spr_path=$2 spr_row=${3:-}
    spr_tmp=$spr_file.tmp.$$
    [ -f "$spr_file" ] || : > "$spr_file"
    awk -v p="$spr_path" '$1 != p { print }' "$spr_file" > "$spr_tmp"
    [ -z "$spr_row" ] || printf '%s\n' "$spr_row" >> "$spr_tmp"
    mv "$spr_tmp" "$spr_file"
}

package_install_one()
{
    path=$list
    case "$path" in
        ''|/*|*@native|*..*|*\ *) echo 'Expected one target PKGPATH without @native' >&2; return 2 ;;
    esac
    [ -f "$state/order" ] && grep -qFx "$path" "$state/order" || {
        echo "PKGPATH is not in the saved order: $path" >&2
        return 2
    }
    # Fail closed on any existing lock, including a stale one. Recovery must
    # never race a controller or silently take over its state directory.
    if ! mkdir "$state/build.lock" 2> /dev/null; then
        other=$(cat "$state/build.lock/pid" 2> /dev/null || :)
        echo "Another build${other:+ ($other)} uses $state" >&2
        return 2
    fi
    printf '%s\n' "$$" > "$state/build.lock/pid"
    run=
    recovery_cleanup()
    {
        [ -z "$run" ] || rm -rf "$run"
        rm -f "$state/build.lock/pid"
        rmdir "$state/build.lock" 2> /dev/null || :
    }
    trap recovery_cleanup EXIT
    stop=0
    trap 'stop=1' HUP INT TERM
    run=$(mktemp -d "$state/package-install.run.XXXXXX") || {
        echo 'Cannot create a private package-install run directory' >&2
        return 2
    }
    mkdir -p "$state/locks"
    vars_cache=
    gnu_stat=no
    clean=clean
    stage_local=yes
    job=1
    cpus=$(host_cpus)
    make_jobs=${CROSS_BULK_MAKE_JOBS:-$cpus}
    count CROSS_BULK_MAKE_JOBS "$make_jobs"
    real_pkg_add=$(var pkgtools/pkg_install NATIVE_PKG_ADD_CMD)
    [ -n "$real_pkg_add" ] || { echo 'NATIVE_PKG_ADD_CMD is empty' >&2; return 2; }
    pkg_add_wrapper "$real_pkg_add" > "$run/pkg_add"
    chmod +x "$run/pkg_add"
    target_pkg_info=$(var pkgtools/pkg_install PKG_INFO)
    [ -n "$target_pkg_info" ] || { echo 'The target PKG_INFO is empty' >&2; return 2; }
    packages=$(var pkgtools/pkg_install PACKAGES)/All
    native_packages=${packages%/All}-native
    target_settings=$(var pkgtools/pkg_install CROSSTARGETSETTINGS)
    stamp=$(date '+%Y%m%d%H%M%S')
    link_launcher_args
    key=$(echo "$path" | tr / _)
    node=$path
    reported=
    shared_pairs_configure
    if ! shared_pair_reset_stage "$path"; then
        echo "Could not reset the shared package stage: $path" >&2
        state_path_row "$state/failed" "$path" "$path shared-stage-cleanup"
        state_path_row "$state/blocked" "$path" "$path shared-stage-cleanup"
        return 1
    fi
    [ "$stop" = 0 ] || return 143
    build_one "$path"
    outcome=$(cat "$run/$key.result" 2>/dev/null || :)
    set -f
    set -- $outcome
    set +f
    case "${1:-}" in
        built)
            shift 2
            state_path_row "$state/done" "$path" "$path $*"
            state_path_row "$state/failed" "$path"
            state_path_row "$state/blocked" "$path"
            echo "Installed $path from its current pkgsrc stage"
            [ "$stop" = 0 ] || return 143
            shared_pair_for_path "$path"
            if [ -n "$shared_pair" ] && [ "$path" = "$shared_producer" ] && shared_pair_ready "$path"; then
                producer_path=$path
                partner=$shared_consumer
                key=$(echo "$partner" | tr / _)
                node=$partner
                log=$state/logs/$key.log
                reported=
                if ! shared_pair_reset_stage "$partner" >> "$log" 2>&1; then
                    state_path_row "$state/failed" "$partner" "$partner shared-stage-cleanup"
                    state_path_row "$state/blocked" "$partner" "$partner shared-stage-cleanup"
                    echo "Could not reset the consumer package stage; retained producer WRKDIR: $producer_path" >&2
                    return 1
                fi
                [ "$stop" = 0 ] || return 143
                build_one "$partner"
                outcome=$(cat "$run/$key.result" 2>/dev/null || :)
                set -f
                set -- $outcome
                set +f
                case "${1:-}" in
                    built)
                        shift 2
                        state_path_row "$state/done" "$partner" "$partner $*"
                        state_path_row "$state/failed" "$partner"
                        state_path_row "$state/blocked" "$partner"
                        echo "Installed paired package $partner from the retained $shared_pair stage"
                        ;;
                    *)
                        reason=${outcome#failed "$partner" }
                        state_path_row "$state/failed" "$partner" "$partner ${reason:-package-install}"
                        state_path_row "$state/blocked" "$partner"
                        echo "Paired package stage failed; retained producer WRKDIR: $producer_path" >&2
                        return 1
                        ;;
                esac
            fi
            ;;
        done)
            echo "$path is already recorded done"
            ;;
        *)
            case "${1:-}" in
                skipped)
                    echo "Package is skipped by the current profile: $outcome" >&2
                    return 2
                    ;;
            esac
            reason=${outcome#failed "$path" }
            state_path_row "$state/failed" "$path" "$path ${reason:-package-install}"
            state_path_row "$state/blocked" "$path"
            echo "Package stage failed; retained WRKDIR: $path" >&2
            return 1
            ;;
    esac
    [ "$stop" = 0 ] || return 143
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
    count CROSS_BULK_MAKE_JOBS "$make_jobs"
    [ -n "${CROSS_BULK_MAKE_JOBS:-}" ] || [ "$make_jobs" -le "$cpus" ] || make_jobs=$cpus
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
    native_info
    target_pkg_info=$(var pkgtools/pkg_install PKG_INFO)
    [ -n "$target_pkg_info" ] || { echo 'The target PKG_INFO is empty' >&2; exit 2; }
    target_settings=$(var pkgtools/pkg_install CROSSTARGETSETTINGS)
    stamp=$(date '+%Y%m%d%H%M%S')
    vars_cache=
    if [ "${CROSS_BULK_VARS_CACHE:-yes}" != no ]; then
        vars_cache=$state/vars
        mkdir -p "$vars_cache"
        gnu_stat=no
        ! stat -c %i / > /dev/null 2>&1 || gnu_stat=yes
    fi
    shared_pairs_configure
    trash_init
    deleter_pid=
    if [ -n "$trash" ]; then
        deleter $$ < /dev/null > /dev/null 2>&1 &
        deleter_pid=$!
    fi
    job=0
    # The native nodes that a target package needs as a tool.
    awk '$1 ~ /@native$/ && $2 !~ /@native$/ { print $1 }' "$state/edges" | sort -u > "$run/crossfed"
    # Keep the results of an earlier run, but try its failures again.
    for list_name in failed blocked; do
        [ -s "$state/$list_name" ] && mv "$state/$list_name" "$state/$list_name.$stamp"
    done
    touch "$state/done" "$state/failed" "$state/blocked" "$state/skipped"
    packages=$(var pkgtools/pkg_install PACKAGES)/All
    native_packages=${packages%/All}-native
    link_launcher_args
    echo "Building with $workers packages at once, MAKE_JOBS=$make_jobs ($cpus CPUs)"
    [ -z "$link_args" ] || echo "Heavy links through $CROSS_BULK_LINK_LAUNCHER"
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
            # A request of a job that ended without its replace.
            res=${res%.result}
            rm -f "$res.result" "$res.replace" "$res.replacing"
            running=$((running - 1))
            changed=1
        done
        # Give one waiting job its replace when every running job waits
        # (see exclusive); start no job while one waits or replaces.
        replacing=0 waiting=0 first=
        for req in "$run"/*.replacing; do
            [ ! -f "$req" ] || replacing=1
        done
        for req in "$run"/*.replace; do
            [ -f "$req" ] || continue
            waiting=$((waiting + 1))
            [ -n "$first" ] || first=$req
        done
        if [ "$replacing" = 0 ] && [ "$waiting" -gt 0 ] && [ "$waiting" -ge "$running" ]; then
            mv "$first" "${first%.replace}.replacing"
            replacing=1 waiting=$((waiting - 1))
        fi
        if [ "$stop" = 1 ]; then
            [ "$running" -gt 0 ] || { echo 'Stopped; the running packages finished' >&2; trap - TERM INT HUP; stop_deleter; rm -rf "$state/build.lock"; return 143; }
        elif [ "$changed" = 1 ] && [ "$running" -lt "$workers" ] && [ "$replacing" = 0 ] && [ "$waiting" = 0 ]; then
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
                    job=$((job + 1))
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
    stop_deleter
    failed=no
    [ ! -s "$state/failed" ] || failed=yes
    [ ! -s "$state/blocked" ] || failed=yes
    rm -rf "$run" "$state/locks" "$state/build.lock"
    [ "$failed" = no ] || return 1
    return 0
}

# The deleter stops with the build (a tree it is removing is finished);
# the next build removes the rest.
stop_deleter()
{
    [ -n "$deleter_pid" ] || return 0
    kill "$deleter_pid" 2> /dev/null || :
    wait "$deleter_pid" 2> /dev/null || :
    deleter_pid=
}

case "$mode" in
    order) order ;;
    deps)
        native_info
        case "$list" in
            *'|'*) key=${list%%\|*}; path=${list#*\|} ;;
            *) key=$(echo "$list" | tr / _); path=$list ;;
        esac
        node_deps "$path" > "$state/$key.tmp" 2> "$state/$key.err" &&
            mv "$state/$key.tmp" "$state/$key.deps" ;;
    fetch) fetch ;;
    build) build ;;
    package-install) package_install_one ;;
    *) echo "Unknown mode: $mode" >&2; exit 2 ;;
esac

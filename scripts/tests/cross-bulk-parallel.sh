#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). scripts/cross-bulk.sh build runs several
# packages at once on a small graph with a recording bmake: independent
# packages overlap, a package starts only after its dependencies are
# installed, installs into one package database never overlap, a failure
# blocks its dependents transitively, a skipped dependency blocks too,
# MAKE_JOBS is split over the packages, a second run builds only the failure
# again, and SIGTERM lets the running packages finish but starts no new one.
# Usage: cross-bulk-parallel.sh NEW_OUTPUT
set -eu
[ "$#" = 1 ] || { echo 'Usage: cross-bulk-parallel.sh NEW_OUTPUT' >&2; exit 2; }
out=$1
case "$out" in /*) ;; *) echo 'NEW_OUTPUT must be absolute' >&2; exit 2 ;; esac
case "$out" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2 ;; esac
[ ! -e "$out" ] || exit 2
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
mkdir -p "$out/tree/t" "$out/packages/All" "$out/active" "$out/work" "$out/target-db"
: > "$out/errors"
: > "$out/edges"
# PACKAGE DEPENDENCIES...
while read -r pkg deps; do
    mkdir "$out/tree/t/$pkg"
    echo "t/$pkg t/$pkg" >> "$out/edges"
    for dep in $deps; do
        echo "t/$dep t/$pkg" >> "$out/edges"
        echo "$dep" >> "$out/tree/t/$pkg/deps"
    done
done <<'GRAPH'
a
b
c
f
h
d a b
e f
g e
i h
j d c
GRAPH
: > "$out/tree/t/f/fail"
echo 'not for this profile' > "$out/tree/t/h/skip"
# The pkg_add that pkgsrc would run: installs into one database never overlap.
cat > "$out/pkg_add" <<WRAP
#!/bin/sh
[ "\$1" = -K ] || { echo "pkg_add without -K: \$*" >> $out/errors; exit 1; }
db=\$(basename "\$2")
mkdir $out/adding-\$db 2> /dev/null || echo "OVERLAP \$db \$3" >> $out/errors
sleep 0.3
rmdir $out/adding-\$db
: > "\$2/\$3"
WRAP
cat > "$out/bmake" <<WRAP
#!/bin/sh
out=$out
echo "\$*" >> \$out/calls
dir= target= varname= add=
while [ "\$#" -gt 0 ]; do
    case "\$1" in
        -C) dir=\$2; shift 2 ;;
        VARNAME=*) varname=\${1#VARNAME=}; shift ;;
        NATIVE_PKG_ADD_CMD=*) add=\${1#NATIVE_PKG_ADD_CMD=}; shift ;;
        *=*) shift ;;
        *) target=\$1; shift ;;
    esac
done
pkg=\${dir##*/}
work()
{
    [ ! -f \$out/work/\$pkg.built ] || return 0
    for dep in \$(cat \$dir/deps 2> /dev/null); do
        [ -f \$out/packages/All/\$dep-1.0.tgz ] || echo "ORDER \$pkg before \$dep" >> \$out/errors
    done
    mkdir \$out/active/\$pkg
    ls \$out/active | wc -l >> \$out/concurrency
    sleep \${FAKE_SLEEP:-2}
    ls \$out/active | wc -l >> \$out/concurrency
    rmdir \$out/active/\$pkg
    [ ! -f \$dir/fail ] || exit 1
    : > \$out/work/\$pkg.built
}
case "\$target" in
    show-var)
        case "\$varname" in
            EMBERBSD_NATIVE_TOOLSET_VERIFIED) echo fake ;;
            PACKAGES) echo \$out/packages ;;
            NATIVE_PKG_ADD_CMD) echo \$out/pkg_add ;;
            *) echo ;;
        esac ;;
    show-vars) echo "\$pkg-1.0"; echo "\$out/work/\$pkg"; cat \$dir/skip 2> /dev/null || echo ;;
    clean) rm -f \$out/work/\$pkg.built ;;
    depends) ;;
    package) work ;;
    package-install)
        work
        \$add -K \$out/target-db \$pkg || exit 1
        : > \$out/packages/All/\$pkg-1.0.tgz ;;
    *) echo "UNKNOWN \$target" >> \$out/errors; exit 1 ;;
esac
WRAP
chmod +x "$out/bmake" "$out/pkg_add"
fail() { echo "FAIL: $*" >&2; exit 1; }
newstate()
{
    rm -rf "$out/state"
    mkdir "$out/state"
    cp "$out/edges" "$out/state/edges"
    tsort "$out/edges" > "$out/state/order"
}
bulk()
{
    BMAKE=$out/bmake MAKECONF=$out/mk.conf PKGSRCDIR=$out/tree CROSS_BULK_CPUS=6 CROSS_BULK_JOBS=3 \
        sh "$ports/scripts/cross-bulk.sh" build "$out/state/order" "$out/state" > "$out/bulk.log" 2>&1
}
calls() { grep -c -- "-C $out/tree/t/$1 " "$out/calls" || :; }

newstate
: > "$out/calls"
bulk || fail "first build: $(cat "$out/bulk.log")"
[ ! -s "$out/errors" ] || fail "$(cat "$out/errors")"
max=$(sort -n "$out/concurrency" | tail -n 1)
[ "$max" -ge 2 ] || fail "at most $max package built at a time"
[ "$max" -le 3 ] || fail "$max packages at once, more than CROSS_BULK_JOBS=3"
grep -q 'MAKE_JOBS=3 ' "$out/calls" || fail 'MAKE_JOBS is not 1.5 x 6 CPUs / 3 packages'
[ "$(ls "$out/target-db" | tr '\n' ' ')" = 'a b c d j ' ] || fail "installed: $(ls "$out/target-db")"
[ "$(cut -d ' ' -f 1 "$out/state/done" | sort | tr '\n' ' ')" = 't/a t/b t/c t/d t/j ' ] ||
    fail "done: $(cat "$out/state/done")"
[ "$(cat "$out/state/failed")" = 't/f build' ] || fail "failed: $(cat "$out/state/failed")"
[ "$(sort "$out/state/blocked" | tr '\n' ' ')" = 't/e t/f t/g t/e t/i t/h ' ] ||
    fail "blocked: $(cat "$out/state/blocked")"
grep -q '^t/h not for this profile$' "$out/state/skipped" || fail 'h is not skipped'
[ ! -e "$out/state/run" ] && [ ! -e "$out/state/build.lock" ] && [ ! -e "$out/state/locks" ] ||
    fail 'scheduler files left behind'

# A second run parses each done package once and builds the failure again.
: > "$out/calls"
bulk || fail "second build: $(cat "$out/bulk.log")"
for pkg in a b c d j; do
    [ "$(calls $pkg)" = 1 ] || fail "done package $pkg ran bmake $(calls $pkg) times"
done
[ "$(calls f)" = 4 ] || fail "failed package f ran bmake $(calls f) times, expected 4"
[ "$(calls e)" = 0 ] || fail 'blocked package e ran bmake'

# SIGTERM: the running packages finish, nothing new starts.
newstate
: > "$out/calls"
FAKE_SLEEP=3 BMAKE=$out/bmake MAKECONF=$out/mk.conf PKGSRCDIR=$out/tree CROSS_BULK_CPUS=6 CROSS_BULK_JOBS=3 \
    sh "$ports/scripts/cross-bulk.sh" build "$out/state/order" "$out/state" > "$out/bulk.log" 2>&1 &
pid=$!
n=0
until grep -q ' start ' "$out/state/progress" 2> /dev/null; do
    n=$((n + 1)); [ "$n" -lt 100 ] || fail 'no package started'
    sleep 0.1
done
kill -TERM "$pid"
rc=0
wait "$pid" || rc=$?
[ "$rc" = 143 ] || fail "stopped build exited $rc, expected 143"
started=$(grep -c ' start ' "$out/state/progress")
finished=$(grep -c ' done \| FAILED ' "$out/state/progress")
[ "$started" = "$finished" ] || fail "$started started, $finished finished after SIGTERM"
[ "$(calls d)" = 0 ] && [ "$(calls j)" = 0 ] || fail 'a package started after SIGTERM'
echo 'PASS: parallel packages, dependency order, one install per database, blocking, resume and SIGTERM drain'

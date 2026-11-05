#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). scripts/cross-bulk.sh build runs several
# packages at once on a small graph with a recording bmake: independent
# packages overlap, a package starts only after its dependencies are
# installed, installs into one package database never overlap, a failure
# blocks its dependents transitively, a skipped dependency blocks too,
# MAKE_JOBS shares one SDK CPU budget over concurrent packages, a second run builds only the failure
# again without hashing the done packages, a new PKGNAME or a missing
# package file builds a done package again, SIGTERM lets the running
# packages finish but starts no new one, and
# a package gets one build run (package-install) after show-vars and clean.
# Usage: cross-bulk-parallel.sh NEW_OUTPUT
set -eu
[ "$#" = 1 ] || { echo 'Usage: cross-bulk-parallel.sh NEW_OUTPUT' >&2; exit 2; }
out=$1
case "$out" in /*) ;; *) echo 'NEW_OUTPUT must be absolute' >&2; exit 2 ;; esac
case "$out" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2 ;; esac
[ ! -e "$out" ] || exit 2
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
if grep -Eq 'nproc|sysctl -n hw\.ncpu|getconf _NPROCESSORS_ONLN' "$ports/scripts/cross-bulk.sh"; then
    echo 'FAIL: cross-bulk contains a local CPU detector' >&2
    exit 1
fi
mkdir -p "$out/tree/t" "$out/packages/All" "$out/active" "$out/work" "$out/target-db" "$out/bin"
real_shasum=$(command -v shasum)
# mksh can report its sleep builtin. Resolve sleep with the original PATH,
# before the tracing wrapper is installed, to avoid recursive exec.
CROSS_BULK_TEST_BASE_PATH=$PATH
export CROSS_BULK_TEST_BASE_PATH
real_sleep=$out/bin/base-sleep
cat > "$real_sleep" <<'WRAP'
#!/bin/sh
PATH=${CROSS_BULK_TEST_BASE_PATH:?}
export PATH
exec sleep "$@"
WRAP
chmod +x "$real_sleep"
cat > "$out/bin/shasum" <<WRAP
#!/bin/sh
echo "\$*" >> $out/shasum-calls
exec $real_shasum "\$@"
WRAP
cat > "$out/bin/selected-python" <<WRAP
#!/bin/sh
echo "\$*" >> $out/selected-python-calls
case "\$*" in *resolve-jobs.py*) ;; *) exit 2 ;; esac
while [ "\$#" -gt 0 ]; do
    case "\$1" in --jobs) echo "\$2"; exit 0 ;; esac
    shift
done
echo "\${FAKE_CPU_COUNT:-10}"
WRAP
chmod +x "$out/bin/shasum" "$out/bin/selected-python"
cat > "$out/bin/sleep" <<WRAP
#!/bin/sh
if [ "\${TRACE_SLEEP:-}" = yes ]; then
    printf '%s\n' "\$1" >> $out/sleep-requests
    case "\$1" in *.*) printf '%s\n' "\$1" >> $out/sleep-fractions ;; esac
    if [ "\${WAIT_FOR_CAP:-}" = yes ] && [ "\$1" = 1 ]; then : > $out/cap-seen; fi
fi
exec "$real_sleep" "\$@"
WRAP
chmod +x "$out/bin/sleep"
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
real_sleep=$real_sleep
echo "\$*" >> \$out/calls
dir= target= varname= varnames= add= jobs=
while [ "\$#" -gt 0 ]; do
    case "\$1" in
        -C) dir=\$2; shift 2 ;;
        VARNAME=*) varname=\${1#VARNAME=}; shift ;;
        VARNAMES=*) varnames=\${1#VARNAMES=}; shift ;;
        NATIVE_PKG_ADD_CMD=*) add=\${1#NATIVE_PKG_ADD_CMD=}; shift ;;
        MAKE_JOBS=*) jobs=\${1#MAKE_JOBS=}; shift ;;
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
    echo "start \$pkg \$jobs" >> \$out/budget-events
    ls \$out/active | wc -l >> \$out/concurrency
    if [ "\${WAIT_FOR_CAP:-}" = yes ] && [ "\$pkg" = one ]; then
        n=0
        while [ ! -f \$out/cap-seen ] && [ "\$n" -lt 200 ]; do
            "\$real_sleep" 0.05
            n=\$((n + 1))
        done
        [ -f \$out/cap-seen ] || { echo 'cap wait timed out' >> \$out/errors; exit 1; }
    else
        sleep \${FAKE_SLEEP:-2}
    fi
    ls \$out/active | wc -l >> \$out/concurrency
    echo "finish \$pkg \$jobs" >> \$out/budget-events
    rmdir \$out/active/\$pkg
    [ ! -f \$dir/fail ] || exit 1
    : > \$out/work/\$pkg.built
}
case "\$target" in
    show-var)
        case "\$varname" in
            EMBERBSD_NATIVE_TOOLSET_VERIFIED) echo fake ;;
            EMBERBSD_HOST_PYTHON) echo $out/bin/selected-python ;;
            EMBERBSD_SDK_SOURCE) echo $out/sdk ;;
            PACKAGES) echo \$out/packages ;;
            PKG_INFO) echo false ;;
            NATIVE_PKG_ADD_CMD) echo \$out/pkg_add ;;
            *) echo ;;
        esac ;;
    show-vars)
        if [ "\$varnames" = 'EMBERBSD_HOST_PYTHON EMBERBSD_SDK_SOURCE' ]; then
            echo \$out/bin/selected-python
            echo \$out/sdk
        else
            version=\$(cat \$dir/version 2> /dev/null || echo 1.0)
            echo "\$pkg-\$version"; echo "\$out/work/\$pkg"; cat \$dir/skip 2> /dev/null || echo
            echo "\$pkg"; echo "\$version"; echo "\$out/packages/All/\$pkg-\$version.tgz"
        fi ;;
    clean) rm -f \$out/work/\$pkg.built ;;
    depends) ;;
    package) work ;;
    package-install)
        work
        \$add -K \$out/target-db \$pkg || exit 1
        echo \$pkg > \$out/packages/All/\$pkg-\$(cat \$dir/version 2> /dev/null || echo 1.0).tgz ;;
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
# Instrument the selected shell even when it provides a sleep builtin.
# Keep the controller's normal $0 and positional arguments.
run_bulk()
{
    sh -c '
        sleep() { env sleep "$@"; }
        script=$1
        shift
        . "$script"
    ' "$ports/scripts/cross-bulk.sh" "$ports/scripts/cross-bulk.sh" "$@"
}

bulk()
{
    PATH=$out/bin:$PATH BMAKE=$out/bmake MAKECONF=$out/mk.conf PKGSRCDIR=$out/tree CROSS_BULK_CPUS=6 CROSS_BULK_JOBS=3 \
        run_bulk build "$out/state/order" "$out/state" > "$out/bulk.log" 2>&1
}
bulk_trace()
{
    TRACE_SLEEP=yes PATH=$out/bin:$PATH BMAKE=$out/bmake MAKECONF=$out/mk.conf PKGSRCDIR=$out/tree \
        CROSS_BULK_CPUS=6 CROSS_BULK_JOBS=3 \
        run_bulk build "$out/state/order" "$out/state" > "$out/bulk.log" 2>&1
}
bulk_expected_failure()
{
    rc=0
    bulk || rc=$?
    [ "$rc" = 1 ] || fail "build with failed/blocked packages exited $rc, expected 1: $(cat "$out/bulk.log")"
}
bulk_auto_cpus()
{
    PATH=$out/bin:$PATH BMAKE=$out/bmake MAKECONF=$out/mk.conf PKGSRCDIR=$out/tree CROSS_BULK_CPUS= CROSS_BULK_JOBS=3 \
        run_bulk build "$out/state/order" "$out/state" > "$out/bulk.log" 2>&1
}
bulk_makeconf_sentinel()
{
    PATH=$out/bin:$PATH BMAKE=$out/bmake MAKECONF=$out/mk.conf PKGSRCDIR=$out/tree \
        CROSS_BULK_CPUS=6 CROSS_BULK_JOBS=3 CROSS_BULK_MAKE_JOBS=makeconf \
        run_bulk build "$out/state/order" "$out/state" > "$out/sentinel.log" 2>&1
}
budget_bulk()
{
    budget_cpu=$1 budget_workers=$2 budget_jobs=$3 budget_resolved=$4 budget_state=$5
    PATH=$out/bin:$PATH BMAKE=$out/bmake MAKECONF=$out/mk.conf PKGSRCDIR=$out/tree \
        CROSS_BULK_CPUS="$budget_cpu" CROSS_BULK_JOBS="$budget_workers" \
        CROSS_BULK_MAKE_JOBS="$budget_jobs" FAKE_CPU_COUNT="$budget_resolved" FAKE_SLEEP=0.4 \
        run_bulk build "$budget_state/order" "$budget_state" > "$out/budget.log" 2>&1
}
new_budget_state()
{
    budget_count=${1:-6}
    mkdir -p "$out/tree/budget"
    : > "$out/budget-edges"
    budget_index=1
    while [ "$budget_index" -le "$budget_count" ]; do
        budget_pkg=p$budget_index
        mkdir -p "$out/tree/budget/$budget_pkg"
        echo "budget/$budget_pkg budget/$budget_pkg" >> "$out/budget-edges"
        budget_index=$((budget_index + 1))
    done
    rm -rf "$out/budget-state"
    mkdir "$out/budget-state"
    cp "$out/budget-edges" "$out/budget-state/edges"
    tsort "$out/budget-edges" > "$out/budget-state/order"
}
check_budget()
{
    budget_expected=$1 budget_expected_workers=$2 budget_expected_first=$3
    budget_state=$4 budget_count=$5 budget_initial=$6
    [ "$(grep -c '^start ' "$out/budget-events")" = "$budget_count" ] || fail 'budget graph did not run all packages'
    [ "$(grep -c '^finish ' "$out/budget-events")" = "$budget_count" ] || fail 'budget graph did not finish all packages'
    budget_peak=$(awk '$1 == "start" { used += $3; if (used > peak) peak = used }
        $1 == "finish" { used -= $3 } END { print peak + 0 }' "$out/budget-events")
    [ "$budget_peak" -le "$budget_expected" ] || fail "active MAKE_JOBS budget reached $budget_peak, over $budget_expected"
    budget_first=$(awk '$1 == "start" { print $3; n++; if (n == want) exit }' want="$budget_initial" "$out/budget-events" | sort -n | tr '\n' ' ')
    [ -n "$budget_first" ] || fail 'no initial worker allocations recorded'
    [ "$budget_first" = "$budget_expected_first" ] ||
        fail "initial shares were '$budget_first', expected '$budget_expected_first'"
    grep -q "Building with $budget_expected_workers packages at once" "$out/budget.log" ||
        fail "wrong worker count: $(cat "$out/budget.log")"
}
run_budget_case()
{
    budget_cpu=$1 budget_workers=$2 budget_jobs=$3 budget_resolved=$4
    budget_expected=$5 budget_expected_workers=$6 budget_expected_first=$7
    budget_count=${8:-6}
    budget_initial=${9:-$budget_expected_workers}
    new_budget_state "$budget_count"
    : > "$out/budget-events"
    : > "$out/concurrency"
    : > "$out/selected-python-calls"
    budget_bulk "$budget_cpu" "$budget_workers" "$budget_jobs" "$budget_resolved" "$out/budget-state" ||
        fail "budget case failed: cpu=$budget_cpu workers=$budget_workers jobs=$budget_jobs: $(cat "$out/budget.log")"
    check_budget "$budget_expected" "$budget_expected_workers" "$budget_expected_first" "$out/budget-state" "$budget_count" "$budget_initial"
}
reject_budget_case()
{
    budget_cpu=$1 budget_workers=$2 budget_jobs=$3 budget_resolved=$4 budget_message=$5
    new_budget_state
    : > "$out/calls"
    rc=0
    budget_bulk "$budget_cpu" "$budget_workers" "$budget_jobs" "$budget_resolved" "$out/budget-state" || rc=$?
    [ "$rc" = 2 ] || fail "invalid CPU budget exited $rc, expected validation failure: $(cat "$out/budget.log")"
    grep -q "$budget_message" "$out/budget.log" || fail "unclear CPU budget refusal: $(cat "$out/budget.log")"
    ! grep -Eq '(^|[[:space:]])(clean|depends|package|package-install)([[:space:]]|$)' "$out/calls" ||
        fail 'invalid CPU budget started package work'
    [ ! -e "$out/budget-state/run" ] && [ ! -e "$out/budget-state/build.lock" ] ||
        fail 'invalid CPU budget created scheduler state'
}
calls() { grep -c -- "-C $out/tree/t/$1 " "$out/calls" || :; }

newstate
: > "$out/calls"
bulk_expected_failure
[ ! -s "$out/errors" ] || fail "$(cat "$out/errors")"
grep -q 'selected SDK CPU capacity=6' "$out/bulk.log" || fail 'explicit CROSS_BULK_CPUS was not preserved'
[ "$(cat "$out/selected-python-calls")" = "-B -E -S $out/sdk/scripts/resolve-jobs.py --jobs 6" ] || fail 'explicit CROSS_BULK_CPUS did not use the shared resolver'
max=$(sort -n "$out/concurrency" | tail -n 1)
[ "$(calls a)" = 3 ] || fail "package a ran bmake $(calls a) times, expected show-vars, clean, package-install"
[ "$max" -ge 2 ] || fail "at most $max package built at a time"
[ "$max" -le 3 ] || fail "$max packages at once, more than CROSS_BULK_JOBS=3"
grep -q 'MAKE_JOBS=2 ' "$out/calls" || fail 'MAKE_JOBS did not share the 6 CPU budget over 3 workers'
budget_peak=$(awk '$1 == "start" { used += $3; if (used > peak) peak = used }
    $1 == "finish" { used -= $3 } END { print peak + 0 }' "$out/budget-events")
[ "$budget_peak" -le 6 ] || fail "initial active MAKE_JOBS budget reached $budget_peak, over 6"
[ "$(ls "$out/target-db" | tr '\n' ' ')" = 'a b c d j ' ] || fail "installed: $(ls "$out/target-db")"
[ "$(cut -d ' ' -f 1 "$out/state/done" | sort | tr '\n' ' ')" = 't/a t/b t/c t/d t/j ' ] ||
    fail "done: $(cat "$out/state/done")"
[ "$(cat "$out/state/failed")" = 't/f build' ] || fail "failed: $(cat "$out/state/failed")"
[ "$(sort "$out/state/blocked" | tr '\n' ' ')" = 't/e t/f t/g t/e t/i t/h ' ] ||
    fail "blocked: $(cat "$out/state/blocked")"
grep -q '^t/h not for this profile$' "$out/state/skipped" || fail 'h is not skipped'
[ ! -e "$out/state/run" ] && [ ! -e "$out/state/build.lock" ] && [ ! -e "$out/state/locks" ] ||
    fail 'scheduler files left behind'

# The removed sentinel fails before the scheduler creates worker state.
: > "$out/calls"
rc=0
bulk_makeconf_sentinel || rc=$?
[ "$rc" = 2 ] || fail "makeconf sentinel exited $rc, expected validation failure"
grep -q 'CROSS_BULK_MAKE_JOBS must be a positive number: makeconf' "$out/sentinel.log" || fail 'sentinel refusal was unclear'
! grep -Eq '(^|[[:space:]])(clean|depends|package|package-install)([[:space:]]|$)' "$out/calls" || fail 'makeconf sentinel started a package worker'
[ ! -e "$out/state/run" ] && [ ! -e "$out/state/build.lock" ] || fail 'sentinel refusal created scheduler state'

# A second run parses each done package once and builds the failure again.
: > "$out/calls"
: > "$out/shasum-calls"
bulk_expected_failure
for pkg in a b c d j; do
    [ "$(calls $pkg)" = 1 ] || fail "done package $pkg ran bmake $(calls $pkg) times"
done
[ "$(calls f)" = 3 ] || fail "failed package f ran bmake $(calls f) times, expected 3"
[ "$(calls e)" = 0 ] || fail 'blocked package e ran bmake'
if grep -Ev '^-a 256$' "$out/shasum-calls" > "$out/package-hash-calls"; then
    fail "done package archives hashed again: $(cat "$out/package-hash-calls")"
fi

# Without an explicit override, use the selected SDK jobs resolver.
: > "$out/selected-python-calls"
rc=0
bulk_auto_cpus || rc=$?
[ "$rc" = 1 ] || fail "automatic CPU build exited $rc, expected 1: $(cat "$out/bulk.log")"
[ "$(cat "$out/selected-python-calls")" = "-B -E -S $out/sdk/scripts/resolve-jobs.py" ] || fail 'automatic CPU detection did not use the selected SDK resolver'
grep -q 'selected SDK CPU capacity=10' "$out/bulk.log" || fail "SDK resolver result was not used: $(cat "$out/bulk.log")"

# A done package whose PKGNAME changed, or whose package file is gone,
# builds again; a changed package file of a done PKGNAME does not.
echo 1.1 > "$out/tree/t/a/version"
rm "$out/packages/All/c-1.0.tgz"
echo changed > "$out/packages/All/b-1.0.tgz"
: > "$out/calls"
bulk_expected_failure
[ "$(calls a)" = 3 ] || fail "package a with a new PKGNAME ran bmake $(calls a) times, expected 3"
[ "$(calls c)" = 3 ] || fail "package c without its file ran bmake $(calls c) times, expected 3"
[ "$(calls b)" = 1 ] || fail "package b with a changed file ran bmake $(calls b) times, expected 1"
grep -q '^t/a a-1.1 ' "$out/state/done" || fail "no record of a-1.1: $(cat "$out/state/done")"
rm "$out/tree/t/a/version"

# A skipped prerequisite blocks its dependent even without a failed package.
rm "$out/tree/t/f/fail"
newstate
bulk_expected_failure
[ ! -s "$out/state/failed" ] || fail "blocked-only pass recorded a failure: $(cat "$out/state/failed")"
[ "$(cat "$out/state/blocked")" = 't/i t/h' ] || fail "blocked-only state: $(cat "$out/state/blocked")"

# Once the skipped prerequisite is restored, all work completes successfully.
rm "$out/tree/t/h/skip"
newstate
bulk || fail "all-success build: $(cat "$out/bulk.log")"
[ ! -s "$out/state/failed" ] || fail "all-success pass recorded failures: $(cat "$out/state/failed")"
[ ! -s "$out/state/blocked" ] || fail "all-success pass recorded blocked nodes: $(cat "$out/state/blocked")"
[ "$(cut -d ' ' -f 1 "$out/state/done" | sort | tr '\n' ' ')" = 't/a t/b t/c t/d t/e t/f t/g t/h t/i t/j ' ] ||
    fail "all-success done: $(cat "$out/state/done")"

# Completed-node validation should not pay the old fixed one-second scheduler delay.
: > "$out/sleep-requests"
: > "$out/sleep-fractions"
bulk_trace || fail "completed-node pass: $(cat "$out/bulk.log")"
awk '{ if ($1 <= 0.1) short = 1; if ($1 > 1) long = 1 }
     END { if (NR == 0 || !short || long) exit 1 }' "$out/sleep-fractions" ||
    fail "completed-node pass had no prompt bounded waits: $(cat "$out/sleep-requests" | tr '\n' ' ')"

# A genuinely long fake worker must still drive the wait interval to its one-second cap.
mkdir -p "$out/tree/long/one" "$out/long-state"
echo 'long/one long/one' > "$out/long-edges"
cp "$out/long-edges" "$out/long-state/edges"
tsort "$out/long-edges" > "$out/long-state/order"
: > "$out/long-state/done"
: > "$out/long-state/failed"
: > "$out/long-state/blocked"
: > "$out/long-state/skipped"
: > "$out/sleep-requests"
TRACE_SLEEP=yes WAIT_FOR_CAP=yes PATH=$out/bin:$PATH BMAKE=$out/bmake MAKECONF=$out/mk.conf \
    PKGSRCDIR=$out/tree CROSS_BULK_CPUS=6 CROSS_BULK_JOBS=1 \
    run_bulk build "$out/long-state/order" "$out/long-state" > "$out/long.log" 2>&1 ||
    fail "long-worker wait pass: $(cat "$out/long.log")"
grep -Fxq 1 "$out/sleep-requests" ||
    fail "long-worker backoff did not reach its one-second cap: $(cat "$out/sleep-requests" | tr '\n' ' ')"
awk '$1 > 1 { bad = 1 }
     END { if (bad) exit 1 }' "$out/sleep-requests" ||
    fail "long-worker wait did not reach one-second cap: $(cat "$out/sleep-requests" | tr '\n' ' ')"

# The default allocation is one selected-SDK budget, including replacement workers.
run_budget_case 1 '' '' 1 1 1 '1 '
run_budget_case '' '' '' 5 5 3 '1 2 2 '
[ "$(cat "$out/selected-python-calls")" = "-B -E -S $out/sdk/scripts/resolve-jobs.py" ] ||
    fail 'odd default capacity did not use selected SDK resolver'
run_budget_case 6 3 '' 10 6 3 '2 2 2 '
run_budget_case 6 '' 4 10 6 1 '4 '
run_budget_case 6 2 3 10 6 2 '3 3 '
run_budget_case 10 5 '' 10 10 5 '10 ' 1 1
reject_budget_case 6 7 '' 10 'CROSS_BULK_JOBS=7 exceeds resolved CPU capacity=6'
reject_budget_case 6 2 4 10 'CROSS_BULK_JOBS=2 with CROSS_BULK_MAKE_JOBS=4 exceeds resolved CPU capacity=6'
reject_budget_case 6 '' 7 10 'CROSS_BULK_MAKE_JOBS=7 exceeds resolved CPU capacity=6'

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
[ "$(cat "$out/state/build.lock/pid")" = "$pid" ] || fail 'SIGTERM target is not the scheduler PID'
kill -TERM "$pid"
rc=0
wait "$pid" || rc=$?
[ "$rc" = 143 ] || fail "stopped build exited $rc, expected 143"
started=$(grep -c ' start ' "$out/state/progress")
finished=$(grep -c ' done \| FAILED ' "$out/state/progress")
[ "$started" = "$finished" ] || fail "$started started, $finished finished after SIGTERM"
[ "$(calls d)" = 0 ] && [ "$(calls j)" = 0 ] || fail 'a package started after SIGTERM'
echo 'PASS: parallel packages, dependency order, one install per database, blocking, resume and SIGTERM drain'

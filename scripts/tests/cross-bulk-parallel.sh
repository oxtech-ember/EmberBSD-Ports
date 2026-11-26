#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). scripts/cross-bulk.sh build runs several
# packages at once on a small graph with a recording bmake: independent
# packages overlap, a package starts only after its dependencies are
# installed, installs into one package database never overlap, a failure
# blocks its dependents transitively, a skipped dependency blocks too,
# MAKE_JOBS shares one SDK CPU budget over concurrent packages, a second run builds only the failure
# again while checking the done package archives, a new PKGNAME or a missing
# package file builds a done package again, SIGTERM lets the running
# packages finish but starts no new one, and
# a package gets one build run (package-install) after show-vars and clean.
# Usage: cross-bulk-parallel.sh NEW_OUTPUT
set -eu
[ "$#" = 1 ] || { [ "$#" = 2 ] && { [ "$2" = --ninja-tail ] || [ "$2" = --ninja-replace ]; }; } || {
    echo 'Usage: cross-bulk-parallel.sh NEW_OUTPUT [--ninja-tail|--ninja-replace]' >&2
    exit 2
}
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
# The pkg_add wrapper runs pkg_add as the SDK writer of its package database.
: "${CROSS_BULK_TEST_SDK_SOURCE:?Set CROSS_BULK_TEST_SDK_SOURCE to the selected SDK source}"
mkdir -p "$out/sdk/scripts"
ln -s "$CROSS_BULK_TEST_SDK_SOURCE/src" "$out/sdk/src"
ln -s "$CROSS_BULK_TEST_SDK_SOURCE/scripts/prefix-lock.py" "$out/sdk/scripts/prefix-lock.py"
host_python=${CROSS_BULK_TEST_PYTHON:-$(command -v python3)}
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
case "\$*" in
    *resolve-jobs.py*) echo "\$*" >> $out/selected-python-calls ;;
    *stage-local-configure-preserve.py*) exit 0 ;; # covered in the stage fixtures
    *) exec "$host_python" "\$@" ;;
esac
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
mkdir -p "$out/registrations"
cat > "$out/pkg_info" <<WRAP
#!/bin/sh
ref=\${3:-\$2}
case "\${ref##*/}" in
    long|long-[0-9]*|short1|short1-[0-9]*)
        if [ -n "\${TAIL_PKG_INFO:-}" ]; then exec "\$TAIL_PKG_INFO" -K "\$TAIL_WORK/real-db" "\$@"; fi ;;
esac
case "\$1" in
    -e) [ -f "$out/registrations/\$2" ] && echo "\$2" ;;
    -q) case "\$3" in /*) cat "\$3" ;; *) cat "$out/registrations/\$3" ;; esac ;;
    *) exit 1 ;;
esac
WRAP
chmod +x "$out/pkg_info"
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
        _DEPENDS_FILE=*) depends=\${1#*=}; shift ;;
        _RDEPENDS_FILE=*) rdepends=\${1#*=}; shift ;;
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
    elif [ -n "\${CROSS_BULK_TEST_NINJA_PROBE:-}" ]; then
        "\$CROSS_BULK_TEST_HOST_PYTHON" -B "\$CROSS_BULK_TEST_NINJA_PROBE" worker "\$pkg" "\$jobs" || exit 1
    else
        sleep \${FAKE_SLEEP:-2}
    fi
    ls \$out/active | wc -l >> \$out/concurrency
    echo "finish \$pkg \$jobs" >> \$out/budget-events
    rmdir \$out/active/\$pkg
    [ ! -f \$dir/fail ] || { echo "intentional package failure: \$pkg" >&2; exit 1; }
    : > \$out/work/\$pkg.built
}
stage_cookies()
{
    mkdir -p \$out/work/\$pkg
    echo "\$1" > \$out/work/\$pkg/.extract_done
    : > \$out/work/\$pkg/.depends
    : > \$out/work/\$pkg/.rdepends
}
case "\$target" in
    show-var)
        case "\$varname" in
            EMBERBSD_NATIVE_TOOLSET_VERIFIED) echo fake ;;
            EMBERBSD_HOST_PYTHON) echo $out/bin/selected-python ;;
            EMBERBSD_SDK_SOURCE) echo $out/sdk ;;
            PACKAGES) echo \$out/packages ;;
            PKG_INFO) echo \$out/pkg_info ;;
            NATIVE_PKG_ADD_CMD) echo \$out/pkg_add ;;
            *) echo ;;
        esac ;;
    show-vars)
        if [ -f \$dir/vars-fail ]; then echo 'intentional worker metadata failure' >&2; exit 1; fi
        if [ "\$varnames" = 'EMBERBSD_HOST_PYTHON EMBERBSD_SDK_SOURCE' ]; then
            echo \$out/bin/selected-python
            echo \$out/sdk
        else
            version=\$(cat \$dir/version 2> /dev/null || echo 1.0)
            for field in \$varnames; do
                case "\$field" in
                    PKGNAME) echo "\$pkg-\$version" ;;
                    WRKDIR) echo "\$out/work/\$pkg" ;;
                    WRKOBJDIR) echo "\$out/work" ;;
                    PKG_SKIP_REASON) cat \$dir/skip 2> /dev/null || echo ;;
                    PKGBASE) echo "\$pkg" ;;
                    PKGVERSION_NOREV) echo "\$version" ;;
                    PKGFILE) echo "\$out/packages/All/\$pkg-\$version.tgz" ;;
                    .CURDIR) echo "\$dir" ;;
                    .MAKE.MAKEFILES) echo "\$dir/Makefile" ;;
                    *) echo ;;
                esac
            done
        fi ;;
    clean) rm -rf \$out/work/\$pkg \$out/work/\$pkg.built ;;
    *.rdepends|*.depends) : > "\$depends"; : > "\$rdepends" ;;
    _package-clean|depends-clean) : ;;
    depends) ;;
    package) work && stage_cookies "\$pkg-\$(cat \$dir/version 2> /dev/null || echo 1.0)" ;;
    replace) "\$CROSS_BULK_TEST_HOST_PYTHON" -B "\$CROSS_BULK_TEST_NINJA_PROBE" replace "\$pkg" "\$jobs" ;;
    package-install)
        work
        \$add -K \$out/target-db \$pkg || exit 1
        name=\$pkg-\$(cat \$dir/version 2> /dev/null || echo 1.0)
        echo "@name \$name" > \$out/packages/All/\$name.tgz
        cp \$out/packages/All/\$name.tgz \$out/registrations/\$name
        stage_cookies "\$name" ;;
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
        state=$3
        manifest=$state/test-stage-manifest
        root=${state%/*}
        : > "$manifest"
        while IFS= read -r node; do
            echo "$root/work/${node##*/}" >> "$manifest"
        done < "$2"
        CROSS_BULK_STAGE_MANIFEST=$manifest
        CROSS_BULK_SUPERVISED="$PPID|$1|$2|$3"
        export CROSS_BULK_STAGE_MANIFEST CROSS_BULK_SUPERVISED
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
        # Each budget case measures compilation from its own fresh fixture.
        rm -rf "$out/work/$budget_pkg" "$out/work/$budget_pkg.built"
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
# Count actual package-work invocations independently of read-only input queries.
calls() { awk -v dir="$out/tree/t/$1" 'index($0,"-C " dir " ") && $NF ~ /^(clean|package-install|package|replace)$/ {n++} END {print n+0}' "$out/calls"; }

if [ "$#" = 2 ]; then
    : "${CROSS_BULK_TEST_HOST_PYTHON:?}" "${CROSS_BULK_TEST_SDK_SOURCE:?}" "${CROSS_BULK_TEST_NINJA_PROBE:?}"
    : > "$out/edges"
    case "$2" in
        --ninja-tail) packages='long short1 short2 short3 short4'; capacity=10 jobs=5 ;;
        --ninja-replace)
            packages='long short1 next1 next2'; capacity=4 jobs=2
            for next in next1 next2; do
                for prev in long short1; do echo "t/$prev t/$next" >> "$out/edges"; done
            done ;;
    esac
    for pkg in $packages; do
        mkdir -p "$out/tree/t/$pkg"
        echo "t/$pkg t/$pkg" >> "$out/edges"
    done
    newstate
    # The normal scheduler, package-install barrier and selected CPU resolver.
    # The replacement case uses real pkg_add on its isolated database.
    BMAKE=$ports/scripts/tests/cross-bulk-bmake-proxy.sh CROSS_BULK_TEST_REAL_BMAKE=$out/bmake \
        MAKECONF=$out/mk.conf PKGSRCDIR=$out/tree CROSS_BULK_CPUS=$capacity CROSS_BULK_JOBS=$jobs \
        run_bulk build "$out/state/order" "$out/state" > "$out/bulk.log" 2>&1 || {
            cat "$out/bulk.log" >&2
            tail -n 12 "$out"/state/logs/*.worker.log >&2
            exit 1
        }
    exit 0
fi

newstate
: > "$out/calls"
bulk_expected_failure
[ ! -s "$out/errors" ] || fail "$(cat "$out/errors")"
grep -Fxq "intentional package failure: f" "$out/state/logs/t_f.log" ||
    fail 'failed package stderr was not preserved in its package log'
grep -Fq "Package worker log: $out/state/logs/t_f.worker.log" "$out/bulk.log" ||
    fail 'failed package output did not identify its worker log'
grep -q 'selected SDK CPU capacity=6' "$out/bulk.log" || fail 'explicit CROSS_BULK_CPUS was not preserved'
[ "$(cat "$out/selected-python-calls")" = "-B -E -S $out/sdk/scripts/resolve-jobs.py --jobs 6" ] || fail 'explicit CROSS_BULK_CPUS did not use the shared resolver'
max=$(sort -n "$out/concurrency" | tail -n 1)
[ "$(calls a)" = 2 ] || fail "package a ran bmake $(calls a) times, expected clean and package-install"
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
    [ "$(calls $pkg)" = 0 ] || fail "done package $pkg ran bmake $(calls $pkg) times"
done
[ "$(calls f)" = 1 ] || fail "failed package f ran $(calls f) build targets, expected one retry"
[ "$(calls e)" = 0 ] || fail 'blocked package e ran bmake'
for pkg in a b c d j; do
    grep -Fq "$out/packages/All/$pkg-1.0.tgz" "$out/shasum-calls" || fail "missed archive hash: $pkg"
done

# Without an explicit override, use the selected SDK jobs resolver.
: > "$out/selected-python-calls"
rc=0
bulk_auto_cpus || rc=$?
[ "$rc" = 1 ] || fail "automatic CPU build exited $rc, expected 1: $(cat "$out/bulk.log")"
[ "$(cat "$out/selected-python-calls")" = "-B -E -S $out/sdk/scripts/resolve-jobs.py" ] || fail 'automatic CPU detection did not use the selected SDK resolver'
grep -q 'selected SDK CPU capacity=10' "$out/bulk.log" || fail "SDK resolver result was not used: $(cat "$out/bulk.log")"

# A done package whose PKGNAME changed, or whose package file is gone,
# builds again; a changed archive for the recorded PKGNAME fails integrity.
echo 1.1 > "$out/tree/t/a/version"
rm "$out/packages/All/c-1.0.tgz"
echo changed > "$out/packages/All/b-1.0.tgz"
: > "$out/calls"
bulk_expected_failure
[ "$(calls a)" = 2 ] || fail "package a with a new PKGNAME ran bmake $(calls a) times, expected 2"
[ "$(calls c)" = 1 ] || fail "package c without its file ran bmake $(calls c) times, expected 1"
[ "$(calls b)" = 0 ] || fail "package b with a changed file ran bmake $(calls b) times, expected 0"
grep -q '^t/a a-1.1 ' "$out/state/done" || fail "no record of a-1.1: $(cat "$out/state/done")"
grep -q '^t/b archive-integrity$' "$out/state/failed" || fail 'changed archive was trusted'
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
for pkg in a b c d e f g h i j; do rm -rf "$out/work/$pkg" "$out/work/$pkg.built"; done
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
[ ! -e "$out/state/build.lock" ] || fail 'stopped build left its state lock'

# A worker-side show-vars failure happens before the package log is opened.
# Keep its stderr in the worker log and identify that log in the result.
mkdir -p "$out/tree/t/worker-fail" "$out/worker-state"
: > "$out/tree/t/worker-fail/vars-fail"
echo 't/worker-fail t/worker-fail' > "$out/worker-edges"
cp "$out/worker-edges" "$out/worker-state/edges"
tsort "$out/worker-edges" > "$out/worker-state/order"
: > "$out/worker-state/done"
: > "$out/worker-state/failed"
: > "$out/worker-state/blocked"
: > "$out/worker-state/skipped"
rc=0
PATH=$out/bin:$PATH BMAKE=$out/bmake MAKECONF=$out/mk.conf PKGSRCDIR=$out/tree \
    CROSS_BULK_CPUS=6 CROSS_BULK_JOBS=1 \
    run_bulk build "$out/worker-state/order" "$out/worker-state" > "$out/worker.log" 2>&1 || rc=$?
[ "$rc" = 1 ] || fail "worker-side failure exited $rc, expected 1: $(cat "$out/worker.log")"
grep -Fxq 'intentional worker metadata failure' "$out/worker-state/logs/t_worker-fail.worker.log" ||
    fail 'worker-side stderr was not preserved before the package log opened'
grep -Fq "Package worker log: $out/worker-state/logs/t_worker-fail.worker.log" "$out/worker.log" ||
    fail 'worker-side failure did not identify its log'
echo 'PASS: parallel packages, dependency order, one install per database, blocking, resume and SIGTERM drain'

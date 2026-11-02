#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise stage-local package installation.
set -eu
[ "$#" = 1 ] || { echo 'Usage: cross-bulk-package-install.sh NEW_OUTPUT' >&2; exit 2; }
out=$1
case "$out" in /*) ;; *) exit 2 ;; esac
[ ! -e "$out" ] || exit 2
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
mkdir -p "$out/tree/pkgtools/pkg_install" "$out/tree/cat/demo" "$out/work/demo" \
    "$out/packages/All" "$out/db" "$out/state/logs" "$out/sdk/scripts"
host_python=$(command -v python3)
cat > "$out/sdk/scripts/resolve-jobs.py" <<'PY'
print(6)
PY
printf '%s\n' 'cat/demo' > "$out/state/order"
printf '%s\n' 'cat/demo cat/demo' > "$out/state/edges"
printf '%s\n' 'cat/other other-1.0 sha256-old' 'cat/demo demo-1.0 sha256-old' > "$out/state/done"
printf '%s\n' 'cat/demo previous-failure' 'cat/other keep-failure' > "$out/state/failed"
printf '%s\n' 'cat/demo cat/blocked' 'cat/other keep-blocked' > "$out/state/blocked"
: > "$out/work/demo/keep-me"
: > "$out/db/demo-0.9"
: > "$out/packages/All/demo-1.0.tgz"
cat > "$out/pkg_info" <<'WRAP'
#!/bin/sh
db=
while [ "$#" -gt 0 ]; do case "$1" in -K) db=$2; shift 2;; *) shift;; esac; done
for f in "$db"/demo-[0-9]*; do [ -e "$f" ] && { echo "${f##*/}"; exit 0; }; done
exit 1
WRAP
cat > "$out/pkg_add" <<'WRAP'
#!/bin/sh
exit 0
WRAP
cat > "$out/bmake" <<WRAP
#!/bin/sh
out=$out
dir= target= varname= varnames=
for a do echo "\$a" >> \$out/calls; done
while [ "\$#" -gt 0 ]; do
    case "\$1" in
        -C) dir=\$2; shift 2;;
        VARNAME=*) varname=\${1#VARNAME=}; shift;;
        VARNAMES=*) varnames=\${1#VARNAMES=}; shift;;
        *=*) shift;;
        *) target=\$1; shift;;
    esac
done
case "\$target" in
    show-var)
        case "\$varname" in
            EMBERBSD_NATIVE_TOOLSET_VERIFIED) echo fake;;
            NATIVE_PKG_ADD_CMD) echo $out/pkg_add;;
            PKG_INFO) echo "$out/pkg_info -K $out/db";;
            CROSSTARGETSETTINGS) echo TARGET_SETTING=selected;;
            PACKAGES) echo $out/packages;;
            *) echo;;
        esac;;
    show-vars)
        for v in \$varnames; do
            case "\$v" in
                PKGNAME) echo demo-1.0;;
                WRKDIR) echo $out/work/demo;;
                PKGBASE) echo demo;;
                .MAKE.MAKEFILES) echo Makefile;;
                .CURDIR) echo $out/tree/cat/demo;;
                EMBERBSD_HOST_PYTHON) echo $host_python;;
                EMBERBSD_SDK_SOURCE) echo $out/sdk;;
                *) echo;;
            esac
        done;;
    package)
        echo package >> $out/targets
        [ ! -e $out/fail-package ] || exit 1
        if [ -e $out/slow-package ]; then
            : > $out/package-started
            while [ ! -e $out/allow-package ]; do sleep 0.05; done
        fi
        mkdir -p $out/packages/All
        echo package > $out/packages/All/demo-1.0.tgz;;
    package-install)
        echo package-install >> $out/targets
        [ ! -e $out/fail-package ] || exit 1
        mkdir -p $out/packages/All
        echo package > $out/packages/All/demo-1.0.tgz
        : > $out/db/demo-1.0;;
    replace)
        echo replace >> $out/targets
        [ ! -e $out/fail-replace ] || exit 1
        rm -f $out/db/demo-[0-9]*
        : > $out/db/demo-1.0;;
    *) exit 2;;
esac
WRAP
chmod +x "$out/pkg_info" "$out/pkg_add" "$out/bmake"
fail() { echo "FAIL: $*" >&2; exit 1; }
run()
{
    target_state=$1
    make_override=${2:-}
    if [ -n "$make_override" ]; then
        env BMAKE=$ports/scripts/tests/cross-bulk-bmake-proxy.sh CROSS_BULK_TEST_REAL_BMAKE=$out/bmake \
            CROSS_BULK_TEST_CPUS=6 \
            MAKECONF=$out/mk.conf PKGSRCDIR=$out/tree CROSS_BULK_VARS_CACHE=no \
            CROSS_BULK_MAKE_JOBS=$make_override \
            sh "$ports/scripts/cross-bulk.sh" package-install cat/demo "$target_state"
        return
    fi
    BMAKE=$ports/scripts/tests/cross-bulk-bmake-proxy.sh CROSS_BULK_TEST_REAL_BMAKE=$out/bmake \
        CROSS_BULK_TEST_CPUS=6 \
        MAKECONF=$out/mk.conf PKGSRCDIR=$out/tree CROSS_BULK_VARS_CACHE=no \
        sh "$ports/scripts/cross-bulk.sh" package-install cat/demo "$target_state"
}
run "$out/state" > "$out/success.log" 2>&1 || fail "package-install: $(cat "$out/success.log")"
grep -q '^package$' "$out/targets" && grep -q '^replace$' "$out/targets" || fail 'did not package then replace installed version'
grep -q '^MAKE_JOBS=6$' "$out/calls" || fail 'default MAKE_JOBS did not use the SDK CPU budget'
[ -f "$out/work/demo/keep-me" ] || fail 'recovery removed the retained WRKDIR'
grep -q '^cat/demo demo-1.0 [0-9a-f][0-9a-f]*$' "$out/state/done" || fail 'success row/checksum missing'
! grep -q '^cat/demo ' "$out/state/failed" || fail 'success retained target failure'
! grep -q '^cat/demo ' "$out/state/blocked" || fail 'success retained target blocked row'
grep -q '^cat/other other-1.0 sha256-old$' "$out/state/done" || fail 'unrelated success changed'
grep -q '^cat/other keep-failure$' "$out/state/failed" || fail 'unrelated failure changed'
grep -q '^cat/other keep-blocked$' "$out/state/blocked" || fail 'unrelated blocked row changed'
    grep -qx clean "$out/calls" && fail 'recovery invoked clean'

mkdir -p "$out/fresh-state/logs"
printf '%s\n' cat/demo > "$out/fresh-state/order"
printf '%s\n' 'cat/demo cat/demo' > "$out/fresh-state/edges"
: > "$out/fresh-state/done"
: > "$out/fresh-state/failed"
: > "$out/fresh-state/blocked"
rm -f "$out/db"/demo-[0-9]* "$out/packages/All/demo-1.0.tgz"
: > "$out/targets"
run "$out/fresh-state" > "$out/fresh.log" 2>&1 || fail "fresh package-install: $(cat "$out/fresh.log")"
grep -q '^package-install$' "$out/targets" || fail 'new package did not use package-install target'
grep -q '^cat/demo demo-1.0 ' "$out/fresh-state/done" || fail 'fresh package was not recorded'
[ -f "$out/work/demo/keep-me" ] || fail 'fresh package recovery removed the retained WRKDIR'

mkdir -p "$out/override-state/logs"
printf '%s\n' cat/demo > "$out/override-state/order"
printf '%s\n' 'cat/demo cat/demo' > "$out/override-state/edges"
: > "$out/override-state/done"
: > "$out/override-state/failed"
: > "$out/override-state/blocked"
rm -f "$out/packages/All/demo-1.0.tgz"
run "$out/override-state" 2 > "$out/override.log" 2>&1 || fail "explicit MAKE_JOBS: $(cat "$out/override.log")"
grep -q '^MAKE_JOBS=2$' "$out/calls" || fail 'explicit MAKE_JOBS override was ignored'

mkdir -p "$out/sentinel-state/logs"
printf '%s\n' cat/demo > "$out/sentinel-state/order"
printf '%s\n' 'cat/demo cat/demo' > "$out/sentinel-state/edges"
: > "$out/sentinel-state/done"
: > "$out/sentinel-state/failed"
: > "$out/sentinel-state/blocked"
: > "$out/targets"
: > "$out/calls"
rc=0
run "$out/sentinel-state" makeconf > "$out/sentinel.log" 2>&1 || rc=$?
[ "$rc" = 2 ] || fail "makeconf sentinel exited $rc, expected validation failure"
grep -q 'CROSS_BULK_MAKE_JOBS must be a positive number: makeconf' "$out/sentinel.log" || fail 'sentinel refusal was unclear'
[ ! -s "$out/targets" ] || fail 'makeconf sentinel started a package target'
! grep -Eq '(^|[[:space:]])(clean|depends|package|package-install)([[:space:]]|$)' "$out/calls" || fail 'makeconf sentinel started a package worker'
[ ! -e "$out/sentinel-state/build.lock" ] || fail 'sentinel refusal left a build lock'

cp "$out/state/done" "$out/done.before"
cp "$out/state/failed" "$out/failed.before"
rm -f "$out/packages/All/demo-1.0.tgz"
: > "$out/fail-replace"
if run "$out/state" > "$out/failure.log" 2>&1; then fail 'failed replace returned success'; fi
cmp -s "$out/state/done" "$out/done.before" || fail 'failure changed successful done rows'
grep -q '^cat/demo ' "$out/state/failed" || fail 'failure was not recorded'
[ -f "$out/work/demo/keep-me" ] || fail 'failure removed retained WRKDIR'

mkdir "$out/state/build.lock"
echo "$$" > "$out/state/build.lock/pid"
if run "$out/state" > "$out/locked.log" 2>&1; then fail 'active build lock was ignored'; fi
grep -q 'Another build' "$out/locked.log" || fail 'lock refusal was unclear'

mkdir -p "$out/signal-state/logs"
printf '%s\n' cat/demo > "$out/signal-state/order"
printf '%s\n' 'cat/demo cat/demo' > "$out/signal-state/edges"
: > "$out/signal-state/done"
: > "$out/signal-state/failed"
: > "$out/signal-state/blocked"
rm -f "$out/fail-replace"
: > "$out/slow-package"
BMAKE=$ports/scripts/tests/cross-bulk-bmake-proxy.sh CROSS_BULK_TEST_REAL_BMAKE=$out/bmake \
    CROSS_BULK_TEST_CPUS=6 \
    MAKECONF=$out/mk.conf PKGSRCDIR=$out/tree CROSS_BULK_VARS_CACHE=no \
    sh "$ports/scripts/cross-bulk.sh" package-install cat/demo "$out/signal-state" \
    > "$out/signal.log" 2>&1 &
pid=$!
i=0
while [ ! -f "$out/package-started" ] && [ "$i" -lt 100 ]; do sleep 0.05; i=$((i + 1)); done
[ -f "$out/package-started" ] || fail 'signal fixture did not reach active package target'
run_dir=$(find "$out/signal-state" -maxdepth 1 -type d -name 'package-install.run.*' -print | sed -n 1p)
[ -f "$run_dir/pkg_add" ] || fail 'active run wrapper was not created'
kill -TERM "$pid"
sleep 0.1
[ -d "$out/signal-state/build.lock" ] && [ -f "$run_dir/pkg_add" ] || fail 'TERM released the lock before bmake drained'
: > "$out/allow-package"
task_rc=0
if wait "$pid"; then task_rc=0; else task_rc=$?; fi
[ "$task_rc" -eq 143 ] || fail "TERM result was $task_rc, expected drain status 143"
[ ! -e "$out/signal-state/build.lock" ] && [ ! -e "$run_dir" ] || fail 'drained run left its lock or wrapper behind'
grep -q '^cat/demo demo-1.0 ' "$out/signal-state/done" || fail 'drained package success was not recorded'
echo 'PASS: stage-local install/replacement, matching done-row rebuild, CPU jobs, state preservation, lock refusal, TERM drain, no clean'

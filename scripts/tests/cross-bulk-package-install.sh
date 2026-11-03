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
    "$out/work/demo-native" "$out/packages/All" "$out/packages-native/All" \
    "$out/db" "$out/native-db" "$out/state/logs" "$out/sdk/scripts" \
    "$out/tree/mk/package"
host_python=$(command -v python3)
cat > "$out/sdk/scripts/resolve-jobs.py" <<'PY'
print(6)
PY
cat > "$out/tree/mk/package/repackage-metadata-check.py" <<'PY'
#!/usr/bin/env python3
from pathlib import Path
import sys

try:
    if sys.argv[1] != '--stage-local' or len(sys.argv) != 6:
        raise ValueError('bad stage-local arguments')
    work, base, version, current = sys.argv[2:]
    stem = base + '-' + version

    def is_identity(name):
        if name == stem:
            return True
        prefix = stem + 'nb'
        suffix = name[len(prefix):] if name.startswith(prefix) else ''
        return bool(suffix and suffix.isascii() and suffix.isdigit())

    def revision(name):
        if name == stem:
            return 0
        return int(name[len(stem) + 2:])

    identity_cookies = ('.extract_done', '.configure_done', '.build_done')
    later = ('.wrapper_done', '.install_done', '.package_done', '.replace_done')
    cookies = identity_cookies + later
    found = {}
    for name in cookies:
        path = Path(work) / name
        if path.is_symlink():
            raise ValueError('symlinked cookie')
        if path.exists():
            found[name] = path.read_text().strip()
    if not is_identity(current):
        raise ValueError('current package family changed')
    extract = found.get('.extract_done')
    if extract is None:
        if any(name in found for name in cookies[1:]):
            raise ValueError('later phase without extract identity')
        print('fresh')
    else:
        if not is_identity(extract) or any(not is_identity(found[name]) for name in identity_cookies[1:] if name in found):
            raise ValueError('package/upstream identity changed')
        package = found.get('.package_done') or found.get('.install_done') or extract
        if not is_identity(package):
            raise ValueError('package/upstream identity changed')
        current_rev = revision(current)
        old_rev = revision(package)
        print('revision' if current_rev != old_rev else 'same')
except (OSError, ValueError) as error:
    print('stage-local: ' + str(error), file=sys.stderr)
    raise SystemExit(1)
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
query=
while [ "$#" -gt 0 ]; do
    case "$1" in
        -K) db=$2; shift 2;;
        -e) query=$2; shift 2;;
        *) shift;;
    esac
done
for f in "$db"/demo-[0-9]*; do
    [ -e "$f" ] || continue
    installed=${f##*/}
    base=${installed%-*}
    version=${installed#"$base"-}
    prefix=$base'>='
    case "$query" in
        "$base"|"$installed") echo "$installed"; exit 0;;
        "$prefix"*) minimum=${query#"$prefix"}; [ "$version" = "$minimum" ] && { echo "$installed"; exit 0; };;
    esac
done
exit 1
WRAP
cat > "$out/pkg_add" <<'WRAP'
#!/bin/sh
exit 0
WRAP
cat > "$out/bmake" <<WRAP
#!/bin/sh
out=$out
dir= target= varname= varnames= native=no packages=
for a do echo "\$a" >> \$out/calls; done
while [ "\$#" -gt 0 ]; do
    case "\$1" in
        -C) dir=\$2; shift 2;;
        VARNAME=*) varname=\${1#VARNAME=}; shift;;
        VARNAMES=*) varnames=\${1#VARNAMES=}; shift;;
        USE_CROSS_COMPILE=no) native=yes; shift;;
        PACKAGES=*) packages=\${1#PACKAGES=}; shift;;
        *=*) shift;;
        *) target=\$1; shift;;
    esac
done
case "\$target" in
    show-var)
        case "\$varname" in
            EMBERBSD_NATIVE_TOOLSET_VERIFIED) echo fake;;
            NATIVE_PKG_ADD_CMD) echo $out/pkg_add;;
            PKG_INFO) if [ "\$native" = yes ]; then echo "$out/pkg_info -K $out/native-db"; else echo "$out/pkg_info -K $out/db"; fi;;
            CROSSTARGETSETTINGS) echo TARGET_SETTING=selected;;
            PACKAGES) if [ "\$native" = yes ]; then echo $out/packages-native; else echo $out/packages; fi;;
            *) echo;;
        esac;;
    show-vars)
        for v in \$varnames; do
            case "\$v" in
                PKGNAME) echo demo-1.0;;
                PKGVERSION_NOREV) echo 1.0;;
                WRKDIR) if [ "\$native" = yes ]; then echo $out/work/demo-native; else echo $out/work/demo; fi;;
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
        if [ "\$native" = yes ]; then
            mkdir -p \${packages:-$out/packages-native}/All
            echo package > \${packages:-$out/packages-native}/All/demo-1.0.tgz
        else
            mkdir -p $out/packages/All
            echo package > $out/packages/All/demo-1.0.tgz
        fi;;
    package-install)
        echo package-install >> $out/targets
        [ ! -e $out/fail-package ] || exit 1
        mkdir -p $out/packages/All
        echo package > $out/packages/All/demo-1.0.tgz
        : > $out/db/demo-1.0;;
    _package-clean)
        echo _package-clean >> $out/targets;;
    install)
        echo install >> $out/targets
        [ "\$native" = yes ] || exit 2
        mkdir -p $out/native-db
        : > $out/native-db/demo-1.0;;
    replace)
        echo replace >> $out/targets
        [ ! -e $out/fail-replace ] || exit 1
        if [ "\$native" = yes ]; then
            rm -f $out/native-db/demo-[0-9]*
            : > $out/native-db/demo-1.0
        else
            rm -f $out/db/demo-[0-9]*
            : > $out/db/demo-1.0
        fi;;
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
            CROSS_BULK_TEST_HOST_PYTHON=$host_python CROSS_BULK_TEST_SDK_SOURCE=$out/sdk \
            MAKECONF=$out/mk.conf PKGSRCDIR=$out/tree CROSS_BULK_VARS_CACHE=no \
            CROSS_BULK_MAKE_JOBS=$make_override \
            sh "$ports/scripts/cross-bulk.sh" package-install cat/demo "$target_state"
        return
    fi
    BMAKE=$ports/scripts/tests/cross-bulk-bmake-proxy.sh CROSS_BULK_TEST_REAL_BMAKE=$out/bmake \
        CROSS_BULK_TEST_CPUS=6 \
        CROSS_BULK_TEST_HOST_PYTHON=$host_python CROSS_BULK_TEST_SDK_SOURCE=$out/sdk \
        MAKECONF=$out/mk.conf PKGSRCDIR=$out/tree CROSS_BULK_VARS_CACHE=no \
        sh "$ports/scripts/cross-bulk.sh" package-install cat/demo "$target_state"
}
run_native()
{
    target_state=$1
    BMAKE=$ports/scripts/tests/cross-bulk-bmake-proxy.sh CROSS_BULK_TEST_REAL_BMAKE=$out/bmake \
        CROSS_BULK_TEST_CPUS=6 \
        CROSS_BULK_TEST_HOST_PYTHON=$host_python CROSS_BULK_TEST_SDK_SOURCE=$out/sdk \
        MAKECONF=$out/mk.conf PKGSRCDIR=$out/tree CROSS_BULK_VARS_CACHE=no \
        sh "$ports/scripts/cross-bulk.sh" package-install cat/demo@native "$target_state"
}

mkdir -p "$out/native-state/logs"
printf '%s\n' 'cat/demo@native' > "$out/native-state/order"
printf '%s\n' 'cat/demo@native cat/demo@native' 'cat/demo@native cat/consumer' > "$out/native-state/edges"
printf '%s\n' 'cat/demo@native demo-1.0 native' > "$out/native-state/done"
: > "$out/native-state/failed"
: > "$out/native-state/blocked"
: > "$out/native-db/demo-1.0"
: > "$out/packages-native/All/demo-1.0.tgz"
: > "$out/work/demo-native/keep-native"
: > "$out/targets"
run_native "$out/native-state" > "$out/native.log" 2>&1 || fail "native package-install: $(cat "$out/native.log")"
grep -q '^USE_CROSS_COMPILE=no$' "$out/calls" || fail 'native rebuild did not select native package mode'
grep -q "^PACKAGES=$out/packages-native$" "$out/calls" || fail 'native rebuild did not select native package destination'
grep -q '^TARGET_SETTING=selected$' "$out/calls" || fail 'cross-fed native tool did not receive target settings'
grep -q '^package$' "$out/targets" && grep -q '^replace$' "$out/targets" || fail 'matching installed native package was not rebuilt and replaced'
! grep -qx _package-clean "$out/targets" || fail 'unchanged native PKGNAME invoked _package-clean'
grep -q '^cat/demo@native demo-1.0 native$' "$out/native-state/done" || fail 'native success was not recorded under its canonical role'
[ -f "$out/work/demo-native/keep-native" ] || fail 'native package-install removed the retained WRKDIR'
! grep -qx clean "$out/calls" || fail 'native package-install invoked clean'

mkdir -p "$out/native-fresh-state/logs"
printf '%s\n' 'cat/demo@native' > "$out/native-fresh-state/order"
printf '%s\n' 'cat/demo@native cat/demo@native' > "$out/native-fresh-state/edges"
: > "$out/native-fresh-state/done"
: > "$out/native-fresh-state/failed"
: > "$out/native-fresh-state/blocked"
rm -f "$out/native-db"/demo-[0-9]*
: > "$out/targets"
: > "$out/calls"
run_native "$out/native-fresh-state" > "$out/native-fresh.log" 2>&1 || fail "fresh native package-install: $(cat "$out/native-fresh.log")"
grep -qx install "$out/targets" || fail 'fresh native package did not use install'
! grep -qx replace "$out/targets" || fail 'fresh native package unexpectedly used replace'
grep -q '^cat/demo@native demo-1.0 native$' "$out/native-fresh-state/done" || fail 'fresh native package was not recorded under its role'
[ -f "$out/work/demo-native/keep-native" ] || fail 'fresh native package-install removed the retained WRKDIR'
! grep -qx clean "$out/calls" || fail 'fresh native package-install invoked clean'

mkdir -p "$out/native-failure-state/logs"
printf '%s\n' 'cat/demo@native' > "$out/native-failure-state/order"
printf '%s\n' 'cat/demo@native cat/demo@native' > "$out/native-failure-state/edges"
printf '%s\n' 'cat/demo@native demo-1.0 native' > "$out/native-failure-state/done"
printf '%s\n' 'cat/demo@native preserve-failure' > "$out/native-failure-state/failed"
: > "$out/native-failure-state/blocked"
: > "$out/targets"
: > "$out/calls"
: > "$out/fail-package"
if run_native "$out/native-failure-state" > "$out/native-failure.log" 2>&1; then fail 'native package failure returned success'; fi
grep -q '^cat/demo@native ' "$out/native-failure-state/failed" || fail 'native failure lost its @native role'
grep -q '^cat/demo@native demo-1.0 native$' "$out/native-failure-state/done" || fail 'native failure changed the prior done row'
! grep -q '^cat/demo@native ' "$out/native-failure-state/blocked" || fail 'native failure duplicated its failed row as blocked'
[ -f "$out/work/demo-native/keep-native" ] || fail 'native failure removed the retained WRKDIR'
[ ! -e "$out/native-failure-state/build.lock" ] || fail 'native failure left the stage-local lock'
rm -f "$out/fail-package"

# An incompatible retained extract identity must fail before package cleanup
# or any install/package target is invoked.
mkdir -p "$out/upstream-failure-state/logs"
printf '%s\n' 'cat/demo' > "$out/upstream-failure-state/order"
printf '%s\n' 'cat/demo cat/demo' > "$out/upstream-failure-state/edges"
: > "$out/upstream-failure-state/done"
: > "$out/upstream-failure-state/failed"
: > "$out/upstream-failure-state/blocked"
printf '%s\n' 'demo-0.9nb1' > "$out/work/demo/.extract_done"
: > "$out/targets"
: > "$out/calls"
if run "$out/upstream-failure-state" > "$out/upstream-failure.log" 2>&1; then
    fail 'stage-local upstream mismatch returned success'
fi
[ ! -s "$out/targets" ] || fail 'upstream mismatch reached package/install target'
[ -f "$out/work/demo/keep-me" ] || fail 'upstream mismatch removed retained work'
printf '%s\n' 'demo-1.0nb0' > "$out/work/demo/.extract_done"

: > "$out/targets"
run "$out/state" > "$out/success.log" 2>&1 || fail "package-install: $(cat "$out/success.log")"
grep -q '^package$' "$out/targets" && grep -q '^replace$' "$out/targets" || fail 'did not package then replace installed version'
! grep -qx _package-clean "$out/targets" || fail 'unchanged PKGNAME invoked _package-clean'
grep -q '^MAKE_JOBS=6$' "$out/calls" || fail 'default MAKE_JOBS did not use the SDK CPU budget'
grep -q '^_EMBER_STAGE_LOCAL_PACKAGE_INSTALL=yes$' "$out/calls" || fail 'controller omitted stage-local identity mode'
grep -q '^_EMBER_STAGE_LOCAL_PKGPATH=cat/demo$' "$out/calls" || fail 'controller omitted exact PKGPATH scope'
grep -q "^_EMBER_STAGE_LOCAL_WRKDIR=$out/work/demo$" "$out/calls" || fail 'controller omitted exact WRKDIR scope'
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

mkdir -p "$out/invalid-budget-state/logs"
printf '%s\n' cat/demo > "$out/invalid-budget-state/order"
printf '%s\n' 'cat/demo cat/demo' > "$out/invalid-budget-state/edges"
: > "$out/invalid-budget-state/done"
: > "$out/invalid-budget-state/failed"
: > "$out/invalid-budget-state/blocked"
: > "$out/targets"
: > "$out/calls"
rc=0
run "$out/invalid-budget-state" 7 > "$out/invalid-budget.log" 2>&1 || rc=$?
[ "$rc" = 2 ] || fail "stage-local oversized MAKE_JOBS exited $rc, expected validation failure"
grep -q 'CROSS_BULK_MAKE_JOBS=7 exceeds resolved CPU capacity=6' "$out/invalid-budget.log" ||
    fail "stage-local oversized MAKE_JOBS refusal was unclear: $(cat "$out/invalid-budget.log")"
[ ! -s "$out/targets" ] || fail 'stage-local oversized MAKE_JOBS started a package target'
[ ! -e "$out/invalid-budget-state/build.lock" ] || fail 'stage-local budget refusal left its lock'

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

#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Same-run LLVM package stage handoff.
# Usage: cross-bulk-llvm-shared-stage.sh NEW_OUTPUT [llvm|qtbase]
set -eu
[ "$#" -ge 1 ] && [ "$#" -le 2 ] || { echo 'Usage: cross-bulk-llvm-shared-stage.sh NEW_OUTPUT [llvm|qtbase]' >&2; exit 2; }
out=$1
pair=${2:-llvm}
[ "$pair" = llvm ] || [ "$pair" = qtbase ] || { echo 'Unknown pair' >&2; exit 2; }
case "$out" in /*) ;; *) echo 'NEW_OUTPUT must be absolute' >&2; exit 2 ;; esac
case "$out" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2 ;; esac
[ ! -e "$out" ] || exit 2
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
if [ "$pair" = llvm ]; then
    producer=lang/llvm consumer=lang/llvm-devel producer_dir=llvm consumer_dir=llvm-devel
    shared_var=EMBERBSD_LLVM_SHARED_STAGE producer_name=llvm-23.1.4nb2 consumer_name=llvm-devel-23.1.4nb3
else
    producer=x11/qt6-qtbase consumer=x11/qt6-qtbase-devel producer_dir=qt6-qtbase consumer_dir=qt6-qtbase-devel
    shared_var=EMBERBSD_QTBASE_SHARED_STAGE producer_name=qt6-qtbase-6.12.0nb9 consumer_name=qt6-qtbase-devel-6.12.0nb11
fi

setup()
{
    case_out=$1
    mkdir -p "$case_out/tree/$producer" "$case_out/tree/$consumer" \
        "$case_out/tree/pkgtools/pkg_install" "$case_out/packages/All" "$case_out/work" "$case_out/state"
    : > "$case_out/tree/$producer/Makefile"
    : > "$case_out/tree/$consumer/Makefile"
    : > "$case_out/tree/pkgtools/pkg_install/Makefile"
    cat > "$case_out/pkg_info" <<'WRAP'
#!/bin/sh
exit 1
WRAP
    cat > "$case_out/pkg_add" <<'WRAP'
#!/bin/sh
exit 0
WRAP
    cat > "$case_out/bmake" <<'WRAP'
#!/bin/sh
out=${FAKE_OUT:?}
producer=${FAKE_PRODUCER:?} consumer=${FAKE_CONSUMER:?}
producer_name=${FAKE_PRODUCER_NAME:?} consumer_name=${FAKE_CONSUMER_NAME:?}
dir= target= varname= varnames= packages=$out/packages work_override= shared=
while [ "$#" -gt 0 ]; do
    case "$1" in
        -C) dir=$2; shift 2 ;;
        VARNAME=*) varname=${1#VARNAME=}; shift ;;
        VARNAMES=*) varnames=${1#VARNAMES=}; shift ;;
        PACKAGES=*) packages=${1#PACKAGES=}; shift ;;
        WRKDIR=*) work_override=${1#WRKDIR=}; shift ;;
        EMBERBSD_LLVM_SHARED_STAGE=*|EMBERBSD_QTBASE_SHARED_STAGE=*) shared=${1#*=}; shift ;;
        *=*) shift ;;
        *) target=$1; shift ;;
    esac
done
pkg=${dir##*/}
base=$pkg
name=$producer_name
[ "$dir" != "$out/tree/$consumer" ] || { base=${consumer##*/}; name=$consumer_name; }
work=${work_override:-$out/work/$pkg}
case "$target" in
    show-var)
        case "$varname" in
            EMBERBSD_NATIVE_TOOLSET_VERIFIED) echo fake ;;
            PACKAGES) echo "$out/packages" ;;
            PKG_INFO|NATIVE_PKG_ADD_CMD) echo "$out/pkg_info" ;;
            CROSSTARGETSETTINGS) echo TARGET_SETTING=selected ;;
            *) echo ;;
        esac ;;
    show-vars)
        for v in $varnames; do
            case "$v" in
                PKGNAME) echo "$name" ;;
                WRKDIR) echo "$work" ;;
                PKGBASE) echo "$base" ;;
                PKG_SKIP_REASON) echo ;;
                .MAKE.MAKEFILES) echo "$dir/Makefile" ;;
                .CURDIR) echo "$dir" ;;
                LLVM_VERSION) echo 23.1.4 ;;
                WRKSRC) echo "$out/work/llvm-project-23.1.4/llvm" ;;
                DISTNAME) echo llvm-project-23.1.4.src ;;
                PATCHDIR) echo "$out/tree/lang/llvm/patches" ;;
                DISTINFO_FILE) echo "$out/tree/lang/llvm/distinfo" ;;
                CMAKE_CONFIGURE_ARGS)
                    if [ "${FAKE_MISMATCH:-no}" = yes ] && [ "$dir" = "$out/tree/$consumer" ]; then echo different; else echo shared; fi ;;
                *) echo shared ;;
            esac
        done ;;
    clean)
        echo "clean:$pkg" >> "$out/calls"
        rm -rf "$work" ;;
    _package-clean)
        echo "_package-clean:$pkg" >> "$out/calls"
        rm -rf "$work/.destdir"
        rm -f "$work/.install_done" "$work/.package_done" ;;
    package-install|package|replace)
        echo "${target}:$pkg${shared:+:shared}" >> "$out/calls"
        if { [ "$dir" = "$out/tree/$producer" ] || [ "$dir" = "$out/tree/$consumer" ]; } && [ -n "$shared" ] &&
            { [ -e "$work/.destdir/stale" ] || [ -e "$work/.install_done" ] || [ -e "$work/.package_done" ]; }; then
            echo 'stale consumer install state survived package cleanup' >&2
            exit 1
        fi
        if [ "$dir" = "$out/tree/$consumer" ] && [ -z "$shared" ]; then
            echo "compile:$pkg" >> "$out/calls"
        fi
        if [ "$dir" = "$out/tree/$producer" ] && [ -n "$shared" ]; then
            mkdir -p "$shared"
            : > "$shared/full-stage"
            if [ "${FAKE_STOP_AFTER_PRODUCER:-no}" = yes ]; then
                kill -TERM "$PPID"
            fi
        fi
        if [ "$dir" = "$out/tree/$consumer" ] && [ -n "$shared" ] && [ ! -f "$shared/full-stage" ]; then
            echo 'SDK was given a missing shared stage' >&2
            exit 1
        fi
        if [ "$dir" = "$out/tree/$consumer" ] && [ "${FAKE_DEVEL_FAIL:-no}" = yes ]; then exit 1; fi
        mkdir -p "$work" "$packages/All"
        : > "$work/built"
        : > "$packages/All/$name.tgz" ;;
    *) echo "unknown target $target" >&2; exit 2 ;;
esac
WRAP
    chmod +x "$case_out/pkg_info" "$case_out/pkg_add" "$case_out/bmake"
    printf '%s\n' "$producer" "$consumer" > "$case_out/state/order"
    printf '%s %s\n' "$producer" "$consumer" > "$case_out/state/edges"
}

run_build()
{
    case_out=$1 mode=${2:-build}
        FAKE_OUT=$case_out FAKE_PRODUCER=$producer FAKE_CONSUMER=$consumer \
        FAKE_PRODUCER_NAME=$producer_name FAKE_CONSUMER_NAME=$consumer_name \
        FAKE_STOP_AFTER_PRODUCER=${FAKE_STOP_AFTER_PRODUCER:-no} \
        FAKE_MISMATCH=${FAKE_MISMATCH:-no} FAKE_DEVEL_FAIL=${FAKE_DEVEL_FAIL:-no} \
        BMAKE=$ports/scripts/tests/cross-bulk-bmake-proxy.sh CROSS_BULK_TEST_REAL_BMAKE=$case_out/bmake \
        MAKECONF=$case_out/mk.conf \
        PKGSRCDIR=$case_out/tree CROSS_BULK_CPUS=1 CROSS_BULK_JOBS=1 \
        CROSS_BULK_MAKE_JOBS=1 CROSS_BULK_TRASH=no CROSS_BULK_VARS_CACHE=no \
        CROSS_BULK_CLEAN_SUCCESS=${CLEAN_SUCCESS:-yes} CROSS_BULK_SHARED_BUILD=yes \
        sh "$ports/scripts/cross-bulk.sh" "$mode" "$producer" "$case_out/state" \
        > "$case_out/build.log" 2>&1
}

fail() { echo "FAIL: $*" >&2; exit 1; }

success=$out/success
setup "$success"
mkdir -p "$success/work/llvm/.llvm-shared-full-stage"
: > "$success/work/llvm/.llvm-shared-full-stage/stale"
run_build "$success" || fail "matching inputs: $(cat "$success/build.log")"
grep -q "^package-install:$producer_dir:shared$" "$success/calls" || fail 'producer did not receive shared-stage path'
grep -q "^package-install:$consumer_dir:shared$" "$success/calls" || fail 'consumer did not consume producer shared stage'
if grep -q "^compile:$consumer_dir$" "$success/calls"; then fail 'consumer compiled again after a matching producer build'; fi
grep -q "^$consumer $consumer_name " "$success/state/done" || fail 'consumer package not recorded done'
if [ -d "$success/work/$producer_dir" ]; then fail 'producer workdir survived successful consumer packaging with cleanup enabled'; fi
last_consumer=$(awk -v p="package-install:$consumer_dir:shared" '$0 == p { n = NR } END { print n + 0 }' "$success/calls")
last_producer_clean=$(awk -v p="clean:$producer_dir" '$0 == p { n = NR } END { print n + 0 }' "$success/calls")
[ "$last_producer_clean" -gt "$last_consumer" ] || fail 'producer stage was cleaned before consumer completed'
if [ -f "$success/work/$producer_dir/.${pair}-shared-full-stage/stale" ]; then fail 'prepare_wrkdir retained an old shared stage'; fi

mismatch=$out/mismatch
setup "$mismatch"
FAKE_MISMATCH=yes run_build "$mismatch" || fail "input mismatch fallback: $(cat "$mismatch/build.log")"
if grep -q ':shared$' "$mismatch/calls"; then fail 'mismatched build inputs reused the shared stage'; fi
grep -q "^package-install:$consumer_dir$" "$mismatch/calls" || fail 'consumer did not use ordinary build after input mismatch'
grep -q "^compile:$consumer_dir$" "$mismatch/calls" || fail 'input mismatch did not fall back to consumer compilation'

failed=$out/failed
setup "$failed"
rc=0
FAKE_MISMATCH=no FAKE_DEVEL_FAIL=yes run_build "$failed" || rc=$?
[ "$rc" = 1 ] || fail "failed SDK run exited $rc, expected 1"
grep -q "^$consumer build$" "$failed/state/failed" || fail 'consumer failure was not recorded'
[ -f "$failed/work/$producer_dir/.${pair}-shared-full-stage/full-stage" ] || fail 'failed consumer removed producer full stage'

cached=$out/cached-runtime
setup "$cached"
: > "$cached/packages/All/$producer_name.tgz"
printf '%s\n' "$producer $producer_name cached" > "$cached/state/done"
FAKE_MISMATCH=no FAKE_DEVEL_FAIL=no run_build "$cached" || fail "cached runtime fallback: $(cat "$cached/build.log")"
if grep -q ':shared$' "$cached/calls"; then fail 'cached runtime without current-run stage was reused'; fi
grep -q "^package-install:$consumer_dir$" "$cached/calls" || fail 'cached producer consumer did not fall back to its regular build'

stage_local=$out/stage-local
setup "$stage_local"
mkdir -p "$stage_local/work/$producer_dir/.destdir" "$stage_local/work/$producer_dir/objects"
: > "$stage_local/work/$producer_dir/.destdir/stale"
: > "$stage_local/work/$producer_dir/.install_done"
: > "$stage_local/work/$producer_dir/.package_done"
: > "$stage_local/work/$producer_dir/objects/compiled.o"
mkdir -p "$stage_local/work/$consumer_dir/.destdir"
: > "$stage_local/work/$consumer_dir/.destdir/stale"
: > "$stage_local/work/$consumer_dir/.install_done"
: > "$stage_local/work/$consumer_dir/.package_done"
CLEAN_SUCCESS=no run_build "$stage_local" package-install || fail "stage-local pair recovery: $(cat "$stage_local/build.log")"
grep -q "^package-install:$producer_dir:shared$" "$stage_local/calls" || fail 'stage-local producer did not receive shared stage'
grep -q "^package-install:$consumer_dir:shared$" "$stage_local/calls" || fail 'stage-local producer recovery did not package its devel partner'
grep -q "^$producer $producer_name " "$stage_local/state/done" || fail 'stage-local producer success was not recorded'
grep -q "^$consumer $consumer_name " "$stage_local/state/done" || fail 'stage-local consumer success was not recorded'
grep -q "^_package-clean:$consumer_dir$" "$stage_local/calls" || fail 'stage-local consumer package state was not reset'
grep -q "^_package-clean:$producer_dir$" "$stage_local/calls" || fail 'stage-local producer package state was not reset'
[ -f "$stage_local/work/$producer_dir/objects/compiled.o" ] || fail 'stage-local install reset removed producer build objects'
[ -f "$stage_local/work/$producer_dir/.${pair}-shared-full-stage/full-stage" ] || fail 'stage-local success removed producer stage when clean-success was disabled'

stopped=$out/stopped-before-consumer
setup "$stopped"
rc=0
FAKE_STOP_AFTER_PRODUCER=yes CLEAN_SUCCESS=no run_build "$stopped" package-install || rc=$?
[ "$rc" = 143 ] || fail "stage-local stop after producer exited $rc, expected 143"
grep -q "^package-install:$producer_dir:shared$" "$stopped/calls" || fail 'stopped stage-local run did not finish producer'
if grep -q "^package-install:$consumer_dir" "$stopped/calls"; then fail 'stage-local stop started the consumer after TERM'; fi
if grep -q "^_package-clean:$consumer_dir$" "$stopped/calls"; then fail 'stage-local stop started consumer cleanup after TERM'; fi
grep -q "^$producer $producer_name " "$stopped/state/done" || fail 'stopped stage-local producer success was not recorded'
[ -f "$stopped/work/$producer_dir/.${pair}-shared-full-stage/full-stage" ] || fail 'stopped stage-local run removed producer stage'

echo "PASS: $pair runtime handoff, exact compile-input match, mismatch fallback, failed-consumer retention and cached-producer fallback"

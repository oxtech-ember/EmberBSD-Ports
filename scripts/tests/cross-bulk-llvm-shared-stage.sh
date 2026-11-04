#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Same-run LLVM package stage handoff.
# Usage: CROSS_BULK_TEST_HOST_PYTHON=... CROSS_BULK_TEST_SDK_SOURCE=...
#        cross-bulk-llvm-shared-stage.sh NEW_OUTPUT [llvm|qtbase|icu]
set -eu
: "${CROSS_BULK_TEST_HOST_PYTHON:?Select the SDK host Python}"
: "${CROSS_BULK_TEST_SDK_SOURCE:?Select the SDK source}"
[ "$#" -ge 1 ] && [ "$#" -le 2 ] || { echo 'Usage: cross-bulk-llvm-shared-stage.sh NEW_OUTPUT [llvm|qtbase|icu]' >&2; exit 2; }
out=$1
pair=${2:-llvm}
[ "$pair" = llvm ] || [ "$pair" = qtbase ] || [ "$pair" = icu ] || { echo 'Unknown pair' >&2; exit 2; }
case "$out" in /*) ;; *) echo 'NEW_OUTPUT must be absolute' >&2; exit 2 ;; esac
case "$out" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2 ;; esac
[ ! -e "$out" ] || exit 2
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
if [ "$pair" = llvm ]; then
    producer=lang/llvm consumer=lang/llvm-devel producer_dir=llvm consumer_dir=llvm-devel
    shared_var=EMBERBSD_LLVM_SHARED_STAGE producer_name=llvm-23.1.4nb2 consumer_name=llvm-devel-23.1.4nb3
elif [ "$pair" = qtbase ]; then
    producer=x11/qt6-qtbase consumer=x11/qt6-qtbase-devel producer_dir=qt6-qtbase consumer_dir=qt6-qtbase-devel
    shared_var=EMBERBSD_QTBASE_SHARED_STAGE producer_name=qt6-qtbase-6.12.0nb10 consumer_name=qt6-qtbase-devel-6.12.0nb12
else
    producer=textproc/icu consumer=textproc/icu-devel producer_dir=icu consumer_dir=icu-devel
    shared_var=EMBERBSD_ICU_SHARED_STAGE producer_name=icu-79.1nb1 consumer_name=icu-devel-79.1nb1
fi

setup()
{
    case_out=$1
    mkdir -p "$case_out/tree/$producer" "$case_out/tree/$consumer" \
        "$case_out/tree/pkgtools/pkg_install" "$case_out/tree/mk/package" "$case_out/packages/All" "$case_out/work" "$case_out/state"
    : > "$case_out/tree/$producer/Makefile"
    : > "$case_out/tree/$consumer/Makefile"
    : > "$case_out/tree/pkgtools/pkg_install/Makefile"
    # This fixture tests stage handoff, not the separately tested metadata guard.
    printf '%s\n' 'import sys' 'sys.exit(0)' > "$case_out/tree/mk/package/repackage-metadata-check.py"
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
if [ "${CPP+x}" = x ]; then echo 'host CPP leaked into controller bmake' >&2; exit 1; fi
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
        EMBERBSD_LLVM_SHARED_STAGE=*|EMBERBSD_QTBASE_SHARED_STAGE=*|EMBERBSD_ICU_SHARED_STAGE=*) shared=${1#*=}; shift ;;
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
            if [ -n "${FAKE_MISMATCH_FIELD:-}" ] && [ "$v" = "$FAKE_MISMATCH_FIELD" ] && [ "$dir" = "$out/tree/$consumer" ]; then
                echo different
                continue
            fi
            case "$v" in
                PKGNAME) echo "$name" ;;
                WRKDIR) echo "$work" ;;
                PKGBASE) echo "$base" ;;
                PKGVERSION_NOREV) version=${name#"$base"-}; echo "${version%nb*}" ;;
                PKG_SKIP_REASON) echo ;;
                .MAKE.MAKEFILES) echo "$dir/Makefile" ;;
                .CURDIR) echo "$dir" ;;
                LLVM_VERSION) echo 23.1.4 ;;
                WRKSRC) echo "$out/work/llvm-project-23.1.4/llvm" ;;
                DISTNAME) echo llvm-project-23.1.4.src ;;
                PATCHDIR) echo "$out/tree/lang/llvm/patches" ;;
                DISTINFO_FILE) echo "$out/tree/lang/llvm/distinfo" ;;
                CMAKE_CONFIGURE_ARGS|CONFIGURE_ARGS)
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
    package-install|package|replace|stage-install)
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
            if [ -e "$shared/stale-metadata" ]; then
                echo 'stale producer stage survived stage-local recovery' >&2
                exit 1
            fi
            mkdir -p "$shared"
            printf 'fresh metadata\n' > "$shared/metadata"
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
        [ "$target" = stage-install ] || : > "$packages/All/$name.tgz" ;;
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
        CPP=/unexpected/host-cpp FAKE_OUT=$case_out FAKE_PRODUCER=$producer FAKE_CONSUMER=$consumer \
        FAKE_PRODUCER_NAME=$producer_name FAKE_CONSUMER_NAME=$consumer_name \
        FAKE_STOP_AFTER_PRODUCER=${FAKE_STOP_AFTER_PRODUCER:-no} \
        FAKE_MISMATCH=${FAKE_MISMATCH:-no} FAKE_MISMATCH_FIELD=${FAKE_MISMATCH_FIELD:-} FAKE_DEVEL_FAIL=${FAKE_DEVEL_FAIL:-no} \
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
mkdir -p "$success/work/$producer_dir/.${pair}-shared-full-stage"
: > "$success/work/$producer_dir/.${pair}-shared-full-stage/stale"
printf '%s\n' "$producer_name" > "$success/work/$producer_dir/.extract_done"
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

if [ "$pair" = icu ]; then
    for field in CC CXX CPP CFLAGS CXXFLAGS CPPFLAGS LDFLAGS PKG_OPTIONS ABI; do
        field_case=$out/mismatch-$field
        setup "$field_case"
        FAKE_MISMATCH_FIELD=$field run_build "$field_case" || fail "mismatch $field: $(cat "$field_case/build.log")"
        if grep -q ':shared$' "$field_case/calls"; then fail "$field mismatch reused shared stage"; fi
        grep -q "^compile:$consumer_dir$" "$field_case/calls" || fail "$field mismatch did not compile independently"
    done
fi

FAKE_MISMATCH_FIELD=
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

# A completed producer from an earlier run keeps compatible objects, but its
# old run-scoped handoff is gone. Restore only the full install stage.
for stage_kind in missing stale; do
cached_build=$out/cached-runtime-with-build-$stage_kind
setup "$cached_build"
: > "$cached_build/packages/All/$producer_name.tgz"
printf '%s\n' "$producer $producer_name cached" > "$cached_build/state/done"
mkdir -p "$cached_build/work/$producer_dir/objects"
# An earlier extraction/configure revision may legitimately feed a newer
# incrementally rebuilt package; only the completed build must be current.
for phase in extract configure; do
    printf '%s\n' "${producer_name%nb*}" > "$cached_build/work/$producer_dir/.$phase"_done
done
printf '%s\n' "$producer_name" > "$cached_build/work/$producer_dir/.build_done"
# Exercise the actual stage-local preflight from the exported pkgsrc patch.
awk '/^\+\+\+ b\/mk\/package\/repackage-metadata-check.py$/ { inside=1; next }
     inside && /^--- / { exit }
     inside && /^\+/ { print substr($0, 2) }' \
    "$ports/profiles/common-build-tools/patches/pkgsrc-repackage-metadata.patch" > "$cached_build/tree/mk/package/repackage-metadata-check.py"
printf 'retained object\n' > "$cached_build/work/$producer_dir/objects/compiled.o"
# A previous run may have left a stage: it is not current-run proof.
if [ "$stage_kind" = stale ]; then
    mkdir -p "$cached_build/work/$producer_dir/.${pair}-shared-full-stage"
    printf 'stale metadata\n' > "$cached_build/work/$producer_dir/.${pair}-shared-full-stage/stale-metadata"
fi
object_before=$("$CROSS_BULK_TEST_HOST_PYTHON" -c 'import os,sys; s=os.stat(sys.argv[1]); print(s.st_ino, s.st_mtime_ns)' "$cached_build/work/$producer_dir/objects/compiled.o")
CLEAN_SUCCESS=no run_build "$cached_build" || fail "cached producer stage restore: $(cat "$cached_build/build.log")"
grep -q "^stage-install:$producer_dir:shared$" "$cached_build/calls" || fail 'cached producer did not restore its shared stage'
grep -q "^package-install:$consumer_dir:shared$" "$cached_build/calls" || fail 'consumer did not use restored stage'
if grep -Eq "^package-install:$producer_dir(:|$)" "$cached_build/calls"; then fail 'stage restore repackaged producer'; fi
if grep -q "^compile:$consumer_dir$" "$cached_build/calls"; then fail 'consumer rebuilt after stage restore'; fi
[ "$object_before" = "$("$CROSS_BULK_TEST_HOST_PYTHON" -c 'import os,sys; s=os.stat(sys.argv[1]); print(s.st_ino, s.st_mtime_ns)' "$cached_build/work/$producer_dir/objects/compiled.o")" ] || fail 'stage restore changed producer object'
[ -f "$cached_build/work/$producer_dir/.${pair}-shared-full-stage/full-stage" ] || fail 'stage restore did not retain full stage'
[ ! -e "$cached_build/work/$producer_dir/.${pair}-shared-full-stage/stale-metadata" ] || fail 'stale stage was reused'
done

# Never follow a stage symlink while recovering a prior producer.
cached_link=$out/cached-runtime-stage-symlink
setup "$cached_link"
: > "$cached_link/packages/All/$producer_name.tgz"
printf '%s\n' "$producer $producer_name cached" > "$cached_link/state/done"
mkdir -p "$cached_link/work/$producer_dir" "$cached_link/outside"
printf '%s\n' "$producer_name" > "$cached_link/work/$producer_dir/.build_done"
printf 'untouched\n' > "$cached_link/outside/sentinel"
ln -s "$cached_link/outside" "$cached_link/work/$producer_dir/.${pair}-shared-full-stage"
link_rc=0
CLEAN_SUCCESS=no run_build "$cached_link" || link_rc=$?
[ "$link_rc" = 1 ] || fail "symlinked stage must fail, got $link_rc"
grep -q "^$consumer shared-stage-restore$" "$cached_link/state/failed" || fail 'symlinked stage failure not reported'
[ "$(cat "$cached_link/outside/sentinel")" = untouched ] || fail 'stage symlink target was modified'
if grep -q "^compile:$consumer_dir$" "$cached_link/calls"; then fail 'symlink failure silently rebuilt consumer'; fi

# A mismatched build cookie is not evidence of the current producer build.
cached_stale=$out/cached-runtime-stale-build
setup "$cached_stale"
: > "$cached_stale/packages/All/$producer_name.tgz"
printf '%s\n' "$producer $producer_name cached" > "$cached_stale/state/done"
mkdir -p "$cached_stale/work/$producer_dir/objects"
printf 'other-package-1\n' > "$cached_stale/work/$producer_dir/.build_done"
printf 'retained object\n' > "$cached_stale/work/$producer_dir/objects/compiled.o"
CLEAN_SUCCESS=no run_build "$cached_stale" || fail "stale build fallback: $(cat "$cached_stale/build.log")"
if grep -q "^stage-install:$producer_dir" "$cached_stale/calls"; then fail 'stale producer build was reused'; fi
grep -q "^compile:$consumer_dir$" "$cached_stale/calls" || fail 'stale producer did not fall back to consumer build'
[ -f "$cached_stale/work/$producer_dir/objects/compiled.o" ] || fail 'stale producer objects were removed'

stage_local=$out/stage-local
setup "$stage_local"
mkdir -p "$stage_local/work/$producer_dir/.destdir" "$stage_local/work/$producer_dir/objects"
: > "$stage_local/work/$producer_dir/.destdir/stale"
: > "$stage_local/work/$producer_dir/.install_done"
: > "$stage_local/work/$producer_dir/.package_done"
: > "$stage_local/work/$producer_dir/objects/compiled.o"
mkdir -p "$stage_local/work/$producer_dir/.${pair}-shared-full-stage"
printf 'stale metadata\n' > "$stage_local/work/$producer_dir/.${pair}-shared-full-stage/stale-metadata"
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
[ "$(cat "$stage_local/work/$producer_dir/.${pair}-shared-full-stage/metadata")" = 'fresh metadata' ] || fail 'stage-local recovery kept stale post-install metadata instead of the new producer stage'

# A single producer has no handoff stage or consumer. Its successful ordinary
# package-install must not attempt to read shared-*/stage or remove objects.
solo=$out/producer-alone
setup "$solo"
printf '%s\n' "$producer" > "$solo/state/order"
: > "$solo/state/edges"
mkdir -p "$solo/work/$producer_dir/objects"
printf 'retained object\n' > "$solo/work/$producer_dir/objects/compiled.o"
CLEAN_SUCCESS=no run_build "$solo" package-install || fail "producer-alone package-install: $(cat "$solo/build.log")"
grep -q "^package-install:$producer_dir$" "$solo/calls" || fail 'producer-alone did not package normally'
grep -q "^$producer $producer_name " "$solo/state/done" || fail 'producer-alone success was not recorded'
[ "$(cat "$solo/work/$producer_dir/objects/compiled.o")" = 'retained object' ] || fail 'producer-alone lost build objects'
if grep -q "^package-install:$consumer_dir" "$solo/calls"; then fail 'producer-alone started absent consumer'; fi
if grep -q 'No such file' "$solo/build.log"; then fail 'producer-alone accessed absent shared stage'; fi

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

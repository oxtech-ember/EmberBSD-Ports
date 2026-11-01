#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Same-run LLVM package stage handoff.
# Usage: cross-bulk-llvm-shared-stage.sh NEW_OUTPUT
set -eu
[ "$#" = 1 ] || { echo 'Usage: cross-bulk-llvm-shared-stage.sh NEW_OUTPUT' >&2; exit 2; }
out=$1
case "$out" in /*) ;; *) echo 'NEW_OUTPUT must be absolute' >&2; exit 2 ;; esac
case "$out" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2 ;; esac
[ ! -e "$out" ] || exit 2
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)

setup()
{
    case_out=$1
    mkdir -p "$case_out/tree/lang/llvm" "$case_out/tree/lang/llvm-devel" \
        "$case_out/tree/pkgtools/pkg_install" "$case_out/packages/All" "$case_out/work" "$case_out/state"
    : > "$case_out/tree/lang/llvm/Makefile"
    : > "$case_out/tree/lang/llvm-devel/Makefile"
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
dir= target= varname= varnames= packages=$out/packages work_override= shared=
while [ "$#" -gt 0 ]; do
    case "$1" in
        -C) dir=$2; shift 2 ;;
        VARNAME=*) varname=${1#VARNAME=}; shift ;;
        VARNAMES=*) varnames=${1#VARNAMES=}; shift ;;
        PACKAGES=*) packages=${1#PACKAGES=}; shift ;;
        WRKDIR=*) work_override=${1#WRKDIR=}; shift ;;
        EMBERBSD_LLVM_SHARED_STAGE=*) shared=${1#EMBERBSD_LLVM_SHARED_STAGE=}; shift ;;
        *=*) shift ;;
        *) target=$1; shift ;;
    esac
done
pkg=${dir##*/}
base=$pkg
name=$pkg-23.1.4nb2
[ "$pkg" != llvm-devel ] || { base=llvm-devel; name=llvm-devel-23.1.4nb3; }
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
                    if [ "${FAKE_MISMATCH:-no}" = yes ] && [ "$pkg" = llvm-devel ]; then echo different; else echo shared; fi ;;
                *) echo shared ;;
            esac
        done ;;
    clean)
        echo "clean:$pkg" >> "$out/calls"
        rm -rf "$work" ;;
    package-install|package|replace)
        echo "${target}:$pkg${shared:+:shared}" >> "$out/calls"
        if [ "$pkg" = llvm ] && [ -n "$shared" ]; then
            mkdir -p "$shared"
            : > "$shared/full-stage"
        fi
        if [ "$pkg" = llvm-devel ] && [ -n "$shared" ] && [ ! -f "$shared/full-stage" ]; then
            echo 'SDK was given a missing shared stage' >&2
            exit 1
        fi
        if [ "$pkg" = llvm-devel ] && [ "${FAKE_DEVEL_FAIL:-no}" = yes ]; then exit 1; fi
        mkdir -p "$work" "$packages/All"
        : > "$work/built"
        : > "$packages/All/$name.tgz" ;;
    *) echo "unknown target $target" >&2; exit 2 ;;
esac
WRAP
    chmod +x "$case_out/pkg_info" "$case_out/pkg_add" "$case_out/bmake"
    printf '%s\n' 'lang/llvm' 'lang/llvm-devel' > "$case_out/state/order"
    printf '%s\n' 'lang/llvm lang/llvm-devel' > "$case_out/state/edges"
}

run_build()
{
    case_out=$1
    FAKE_OUT=$case_out FAKE_MISMATCH=${FAKE_MISMATCH:-no} FAKE_DEVEL_FAIL=${FAKE_DEVEL_FAIL:-no} \
        BMAKE=$case_out/bmake MAKECONF=$case_out/mk.conf \
        PKGSRCDIR=$case_out/tree CROSS_BULK_CPUS=1 CROSS_BULK_JOBS=1 \
        CROSS_BULK_MAKE_JOBS=1 CROSS_BULK_TRASH=no CROSS_BULK_VARS_CACHE=no \
        CROSS_BULK_CLEAN_SUCCESS=${CLEAN_SUCCESS:-yes} CROSS_BULK_LLVM_SHARED_BUILD=yes \
        sh "$ports/scripts/cross-bulk.sh" build "$case_out/state/order" "$case_out/state" \
        > "$case_out/build.log" 2>&1
}

fail() { echo "FAIL: $*" >&2; exit 1; }

success=$out/success
setup "$success"
mkdir -p "$success/work/llvm/.llvm-shared-full-stage"
: > "$success/work/llvm/.llvm-shared-full-stage/stale"
run_build "$success" || fail "matching inputs: $(cat "$success/build.log")"
grep -q '^package-install:llvm:shared$' "$success/calls" || fail 'runtime did not receive shared-stage path'
grep -q '^package-install:llvm-devel:shared$' "$success/calls" || fail 'SDK did not consume runtime shared stage'
grep -q '^lang/llvm-devel llvm-devel-23.1.4nb3 ' "$success/state/done" || fail 'SDK package not recorded done'
if [ -d "$success/work/llvm" ]; then fail 'producer workdir survived successful SDK packaging with cleanup enabled'; fi
last_sdk=$(awk '$0 == "package-install:llvm-devel:shared" { n = NR } END { print n + 0 }' "$success/calls")
last_runtime_clean=$(awk '$0 == "clean:llvm" { n = NR } END { print n + 0 }' "$success/calls")
[ "$last_runtime_clean" -gt "$last_sdk" ] || fail 'runtime stage was cleaned before SDK consumer completed'
if [ -f "$success/work/llvm/.llvm-shared-full-stage/stale" ]; then fail 'prepare_wrkdir retained an old shared stage'; fi

mismatch=$out/mismatch
setup "$mismatch"
FAKE_MISMATCH=yes run_build "$mismatch" || fail "input mismatch fallback: $(cat "$mismatch/build.log")"
if grep -q ':shared$' "$mismatch/calls"; then fail 'mismatched build inputs reused the shared stage'; fi
grep -q '^package-install:llvm-devel$' "$mismatch/calls" || fail 'SDK did not use ordinary build after input mismatch'

failed=$out/failed
setup "$failed"
FAKE_MISMATCH=no FAKE_DEVEL_FAIL=yes run_build "$failed" || fail 'failed SDK run should be recorded by cross-bulk'
grep -q '^lang/llvm-devel build$' "$failed/state/failed" || fail 'SDK failure was not recorded'
[ -f "$failed/work/llvm/.llvm-shared-full-stage/full-stage" ] || fail 'failed SDK removed runtime full stage'

cached=$out/cached-runtime
setup "$cached"
: > "$cached/packages/All/llvm-23.1.4nb2.tgz"
printf '%s\n' 'lang/llvm llvm-23.1.4nb2 cached' > "$cached/state/done"
FAKE_MISMATCH=no FAKE_DEVEL_FAIL=no run_build "$cached" || fail "cached runtime fallback: $(cat "$cached/build.log")"
if grep -q ':shared$' "$cached/calls"; then fail 'cached runtime without current-run stage was reused'; fi
grep -q '^package-install:llvm-devel$' "$cached/calls" || fail 'cached-runtime SDK did not fall back to its regular build'

echo 'PASS: runtime handoff, exact compile-input match, mismatch fallback, failed-consumer retention and cached-runtime fallback'

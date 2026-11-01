#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Successful workdir cleanup falls back to
# pkgsrc clean when same-filesystem trash is unavailable, preserving native
# settings. Failed packages retain their workdirs.
# Usage: cross-bulk-clean-success-fallback.sh NEW_OUTPUT
set -eu
[ "$#" = 1 ] || { echo 'Usage: cross-bulk-clean-success-fallback.sh NEW_OUTPUT' >&2; exit 2; }
out=$1
case "$out" in /*) ;; *) echo 'NEW_OUTPUT must be absolute' >&2; exit 2 ;; esac
case "$out" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2 ;; esac
[ ! -e "$out" ] || exit 2
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
mkdir -p "$out/tree/t/native" "$out/tree/t/fail" "$out/tree/t/default" "$out/tree/t/cleanup-fail" "$out/packages/All" "$out/work" \
    "$out/native-db" "$out/target-db"
cat > "$out/pkg_info" <<'WRAP'
#!/bin/sh
exit 1
WRAP
cat > "$out/pkg_add" <<'WRAP'
#!/bin/sh
exit 0
WRAP
cat > "$out/bmake" <<WRAP
#!/bin/sh
out=$out
all=\$*
dir= target= varname= varnames= native=no packages=\$out/packages
while [ "\$#" -gt 0 ]; do
    case "\$1" in
        -C) dir=\$2; shift 2 ;;
        VARNAME=*) varname=\${1#VARNAME=}; shift ;;
        VARNAMES=*) varnames=\${1#VARNAMES=}; shift ;;
        USE_CROSS_COMPILE=no) native=yes; shift ;;
        PACKAGES=*) packages=\${1#PACKAGES=}; shift ;;
        *=*) shift ;;
        *) target=\$1; shift ;;
    esac
done
pkg=\${dir##*/}
w=\$out/work/\$pkg
case "\$target" in
    show-var)
        case "\$varname" in
            EMBERBSD_NATIVE_TOOLSET_VERIFIED) echo fake ;;
            PACKAGES) echo \$out/packages ;;
            PKG_INFO|NATIVE_PKG_ADD_CMD) echo \$out/pkg_info ;;
            CROSSTARGETSETTINGS) echo TARGET_SETTING=selected ;;
            WRKOBJDIR) echo \$out/work ;;
            *) echo ;;
        esac ;;
    show-vars)
        for v in \$varnames; do
            case "\$v" in
                PKGNAME) echo \$pkg-1.0 ;;
                WRKDIR) echo \$w ;;
                PKGBASE) echo \$pkg ;;
                *) echo ;;
            esac
        done ;;
    clean)
        echo "clean native=\$native args=\$all" >> \$out/clean-calls
        if [ \$pkg = cleanup-fail ] && [ -f \$w/built ]; then exit 1; fi
        rm -rf \$w ;;
    install|package-install)
        mkdir -p \$w; : > \$w/built
        [ \$pkg != fail ] || exit 1
        mkdir -p \$packages/All
        : > \$packages/All/\$pkg-1.0.tgz ;;
    *) echo "unknown target \$target" >&2; exit 2 ;;
esac
WRAP
chmod +x "$out/pkg_info" "$out/pkg_add" "$out/bmake"
fail() { echo "FAIL: $*" >&2; exit 1; }
mkdir "$out/native-state"
printf '%s\n' 't/native@native' > "$out/native-state/order"
printf '%s\n' 't/native@native t/native' > "$out/native-state/edges"
BMAKE=$ports/scripts/tests/cross-bulk-bmake-proxy.sh CROSS_BULK_TEST_REAL_BMAKE=$out/bmake \
    MAKECONF=$out/mk.conf PKGSRCDIR=$out/tree CROSS_BULK_CPUS=1 CROSS_BULK_JOBS=1 \
    CROSS_BULK_VARS_CACHE=no CROSS_BULK_TRASH=no CROSS_BULK_CLEAN_SUCCESS=yes \
    sh "$ports/scripts/cross-bulk.sh" build "$out/native-state/order" "$out/native-state" \
    > "$out/native.log" 2>&1 || fail "native build: $(cat "$out/native.log")"
grep -q '^t/native@native ' "$out/native-state/done" || fail "native node not done: $(cat "$out/native-state/done")"
[ ! -e "$out/work/native" ] || fail 'native fallback clean left its WRKDIR'
grep -q 'clean native=yes args=.*USE_CROSS_COMPILE=no.*TARGET_SETTING=selected' "$out/clean-calls" ||
    fail "native fallback did not preserve settings: $(cat "$out/clean-calls")"

mkdir "$out/default-state"
printf '%s\n' t/default > "$out/default-state/order"
printf '%s\n' 't/default t/default' > "$out/default-state/edges"
BMAKE=$ports/scripts/tests/cross-bulk-bmake-proxy.sh CROSS_BULK_TEST_REAL_BMAKE=$out/bmake \
    MAKECONF=$out/mk.conf PKGSRCDIR=$out/tree CROSS_BULK_CPUS=1 CROSS_BULK_JOBS=1 \
    CROSS_BULK_VARS_CACHE=no CROSS_BULK_CLEAN_SUCCESS=yes \
    sh "$ports/scripts/cross-bulk.sh" build "$out/default-state/order" "$out/default-state" \
    > "$out/default.log" 2>&1 || fail "default build: $(cat "$out/default.log")"
[ ! -e "$out/work/default" ] || fail 'successful target workdir was not retired to trash'
mkdir -p "$out/work/default"
: > "$out/work/default/reused"
BMAKE=$ports/scripts/tests/cross-bulk-bmake-proxy.sh CROSS_BULK_TEST_REAL_BMAKE=$out/bmake \
    MAKECONF=$out/mk.conf PKGSRCDIR=$out/tree CROSS_BULK_CPUS=1 CROSS_BULK_JOBS=1 \
    CROSS_BULK_VARS_CACHE=no CROSS_BULK_CLEAN_SUCCESS=yes \
    sh "$ports/scripts/cross-bulk.sh" build "$out/default-state/order" "$out/default-state" \
    > "$out/reuse.log" 2>&1 || fail "reuse build: $(cat "$out/reuse.log")"
[ -f "$out/work/default/reused" ] || fail 'cleanup removed a reused package WRKDIR'

mkdir "$out/fail-state"
printf '%s\n' t/fail > "$out/fail-state/order"
printf '%s\n' 't/fail t/fail' > "$out/fail-state/edges"
BMAKE=$ports/scripts/tests/cross-bulk-bmake-proxy.sh CROSS_BULK_TEST_REAL_BMAKE=$out/bmake \
    MAKECONF=$out/mk.conf PKGSRCDIR=$out/tree CROSS_BULK_CPUS=1 CROSS_BULK_JOBS=1 \
    CROSS_BULK_VARS_CACHE=no CROSS_BULK_TRASH=no CROSS_BULK_CLEAN_SUCCESS=yes \
    sh "$ports/scripts/cross-bulk.sh" build "$out/fail-state/order" "$out/fail-state" \
    > "$out/fail.log" 2>&1 || fail "failed package scheduler: $(cat "$out/fail.log")"
grep -q '^t/fail ' "$out/fail-state/failed" || fail "failure was not recorded: $(cat "$out/fail-state/failed")"
[ -f "$out/work/fail/built" ] || fail 'failed package WRKDIR was removed'

mkdir "$out/cleanup-fail-state"
printf '%s\n' t/cleanup-fail > "$out/cleanup-fail-state/order"
printf '%s\n' 't/cleanup-fail t/cleanup-fail' > "$out/cleanup-fail-state/edges"
BMAKE=$ports/scripts/tests/cross-bulk-bmake-proxy.sh CROSS_BULK_TEST_REAL_BMAKE=$out/bmake \
    MAKECONF=$out/mk.conf PKGSRCDIR=$out/tree CROSS_BULK_CPUS=1 CROSS_BULK_JOBS=1 \
    CROSS_BULK_VARS_CACHE=no CROSS_BULK_TRASH=no CROSS_BULK_CLEAN_SUCCESS=yes \
    sh "$ports/scripts/cross-bulk.sh" build "$out/cleanup-fail-state/order" "$out/cleanup-fail-state" \
    > "$out/cleanup-fail.log" 2>&1 || fail "cleanup-failure scheduler: $(cat "$out/cleanup-fail.log")"
grep -q '^t/cleanup-fail cleanup-fail-1.0 ' "$out/cleanup-fail-state/done" ||
    fail "successful package marked incomplete after cleanup failure: $(cat "$out/cleanup-fail-state/done")"
[ -f "$out/packages/All/cleanup-fail-1.0.tgz" ] || fail 'completed package artifact was lost'
[ -f "$out/work/cleanup-fail/built" ] || fail 'failed cleanup removed workdir despite failure'
grep -q '^WARNING: t/cleanup-fail built successfully but WRKDIR cleanup failed:' \
    "$out/cleanup-fail-state/logs/t_cleanup-fail.log" || fail 'cleanup warning missing from package log'
echo 'PASS: native fallback preserves settings; failed work remains; cleanup failure warns without undoing package success'

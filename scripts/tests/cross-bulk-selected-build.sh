#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# A selected build holds the shared state lock across dependency ordering and
# package scheduling, refuses active writers before querying, and never runs
# the build after a failed order pass.
set -eu
[ "$#" = 1 ] || { echo 'Usage: cross-bulk-selected-build.sh NEW_OUTPUT' >&2; exit 2; }
out=$1
case "$out" in /*) ;; *) echo 'NEW_OUTPUT must be absolute' >&2; exit 2 ;; esac
case "$out" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2 ;; esac
[ ! -e "$out" ] || exit 2
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
selected_shell=${CROSS_BULK_TEST_SHELL:-$(command -v sh)}
mkdir -p "$out/tree/pkgtools/pkg_install" "$out/tree/cat/app" \
    "$out/tree/cat/dep" "$out/tree/cat/fail" "$out/packages/All" \
    "$out/native-db" "$out/target-db" "$out/state/logs"
: > "$out/mk.conf"
for p in app dep fail; do : > "$out/tree/cat/$p/Makefile"; done
: > "$out/tree/pkgtools/pkg_install/Makefile"
mkdir -p "$out/tree/mk"
cat > "$out/pkg_info" <<WRAP
#!/bin/sh
exit 1
WRAP
cat > "$out/python" <<WRAP
#!/bin/sh
echo 2
WRAP
cat > "$out/bmake" <<WRAP
#!/bin/sh
out=$out
dir= target= varname= varnames= cross=no
cache=no
for arg do
    case "\$arg" in
        PBULK_CACHE_DIRECTORY=*) cache=yes ;;
        USE_CROSS_COMPILE=no) cross=yes ;;
        VARNAME=*) varname=\${arg#VARNAME=} ;;
        VARNAMES=*) varnames=\${arg#VARNAMES=} ;;
        *=*) ;;
        -C) ;;
        *) ;;
    esac
done
while [ "\$#" -gt 0 ]; do
    case "\$1" in
        -C) dir=\$2; shift 2 ;;
        VARNAME=*) varname=\${1#VARNAME=}; shift ;;
        VARNAMES=*) varnames=\${1#VARNAMES=}; shift ;;
        USE_CROSS_COMPILE=no) cross=yes; shift ;;
        *=*) shift ;;
        *) target=\$1; shift ;;
    esac
done
pkg=\${dir##*/}
printf '%s %s\\n' "\$dir" "\$target" >> "$out/calls"
printf '%s %s %s\\n' "\$cache" "\$target" "\$pkg" >> "$out/cache-calls"
case "\$target" in
    show-var)
        case "\$varname" in
            EMBERBSD_NATIVE_TOOLSET_VERIFIED) echo fake ;;
            EMBERBSD_HOST_PYTHON) echo "$out/python" ;;
            EMBERBSD_SDK_SOURCE) echo "$out/sdk" ;;
            PACKAGES) echo "$out/packages" ;;
            PKG_INFO) if [ "\$cross" = yes ]; then echo "$out/pkg_info -K $out/native-db"; else echo "$out/pkg_info -K $out/target-db"; fi ;;
            NATIVE_PKG_ADD_CMD) echo "$out/pkg_add" ;;
            _PKG_DBDIR) echo "$out/target-db" ;;
            _HOST_PKG_DBDIR) echo "$out/native-db" ;;
            CROSSTARGETSETTINGS|DISTDIR) echo ;;
            *) echo ;;
        esac ;;
    show-vars)
        if [ "\${SLOW_ORDER:-no}" = yes ] && [ "\$pkg" = app ]; then
            : > "$out/order-worker-active"
            sleep 0.5
            : > "$out/order-worker-drained"
        fi
        if [ "\$pkg" = fail ]; then
            echo 'simulated unreadable dependency metadata' >&2
            exit 1
        fi
        for v in \$varnames; do
            case "\$v" in
                OPSYS) echo NetBSD ;;
                MACHINE_ARCH) echo aarch64 ;;
                MACHINE_GNU_PLATFORM) echo aarch64--netbsd ;;
                EMBERBSD_HOST_PYTHON) echo "$out/python" ;;
                EMBERBSD_SDK_SOURCE) echo "$out/sdk" ;;
                PKG_SKIP_REASON) echo ;;
                DEPENDS) if [ "\$pkg" = app ]; then echo 'dep>=1:../../cat/dep'; else echo ; fi ;;
                BUILD_DEPENDS|TOOL_DEPENDS|BOOTSTRAP_DEPENDS) echo ;;
                PKGBASE) echo "\$pkg" ;;
                PKGNAME) echo "\$pkg-1.0" ;;
                WRKDIR) echo "$out/work/cat/\$pkg" ;;
                .MAKE.MAKEFILES) echo "\$dir/Makefile" ;;
                .CURDIR) echo "\$dir" ;;
                *) echo ;;
            esac
        done ;;
    clean|package|replace) echo "TARGET \$target" >> "$out/targets" ;;
    package-install)
        [ -d "$out/state/build.lock" ] || echo "\$pkg" >> "$out/missing-build-lock"
        echo "TARGET \$target" >> "$out/targets"
        mkdir -p "$out/packages/All"
        : > "$out/packages/All/\$pkg-1.0.tgz" ;;
    *) echo "unknown target: \$target" >&2; exit 2 ;;
esac
WRAP
chmod +x "$out/pkg_info" "$out/python" "$out/bmake"
: > "$out/pkg_add"
chmod +x "$out/pkg_add"
: > "$out/missing-build-lock"
printf '%s\n' cat/app > "$out/roots"

fail() { echo "FAIL: $*" >&2; exit 1; }

# An existing writer lock refuses both graph replacement and combined build
# before bmake or any state file is changed.
printf '%s\n' 'cat/old' > "$out/state/order"
printf '%s\n' 'cat/old cat/old' > "$out/state/edges"
printf '%s\n' 'cat/old cat/old-1.0 old-hash' > "$out/state/done"
mkdir "$out/state/build.lock"
printf '%s\n' "$$" > "$out/state/build.lock/pid"
cp "$out/state/order" "$out/order.before"
cp "$out/state/edges" "$out/edges.before"
cp "$out/state/done" "$out/done.before"
: > "$out/calls"
for mode in order selected-order selected-build; do
    rc=0
    env BMAKE="$out/bmake" MAKECONF="$out/mk.conf" PKGSRCDIR="$out/tree" \
        CROSS_BULK_SHELL="$selected_shell" \
        "$selected_shell" "$ports/scripts/cross-bulk.sh" "$mode" "$out/roots" "$out/state" \
        > "$out/locked-$mode.log" 2>&1 || rc=$?
    [ "$rc" -eq 2 ] || fail "$mode ignored the active writer lock (status $rc)"
    grep -q 'Another build' "$out/locked-$mode.log" || fail "$mode lock refusal was unclear"
done
cmp -s "$out/state/order" "$out/order.before" || fail 'locked planning replaced STATE/order'
cmp -s "$out/state/edges" "$out/edges.before" || fail 'locked planning replaced STATE/edges'
cmp -s "$out/state/done" "$out/done.before" || fail 'locked planning changed STATE/done'
[ ! -s "$out/calls" ] || fail 'locked planning queried bmake'
rm -rf "$out/state/build.lock"

# A signal during order waits for the synchronous xargs frontier to drain;
# the shared lock is removed only after the dependency-query child is done.
rm -f "$out/order-worker-active" "$out/order-worker-drained"
env BMAKE="$out/bmake" MAKECONF="$out/mk.conf" PKGSRCDIR="$out/tree" \
    SLOW_ORDER=yes CROSS_BULK_JOBS=1 CROSS_BULK_SHELL="$selected_shell" \
    "$selected_shell" "$ports/scripts/cross-bulk.sh" order "$out/roots" "$out/state" \
    > "$out/order-signal.log" 2>&1 &
order_pid=$!
i=0
while [ ! -e "$out/order-worker-active" ] && [ "$i" -lt 100 ]; do
    sleep 0.05
    i=$((i + 1))
done
[ -e "$out/order-worker-active" ] || fail 'order query worker did not start'
kill -TERM "$order_pid"
rc=0
wait "$order_pid" || rc=$?
[ "$rc" -eq 143 ] || fail "signalled order exited $rc, expected 143"
[ -e "$out/order-worker-drained" ] || fail 'order released before its query worker drained'
[ ! -e "$out/state/build.lock" ] || fail 'drained order left its state lock'

# If xargs itself reports signal termination, keep the lock because its
# descendants may still be running outside the controller's wait path.
mkdir -p "$out/fake-bin"
cat > "$out/fake-bin/xargs" <<WRAP
#!/bin/sh
(sleep 0.5; : > "$out/xargs-late-child") </dev/null >/dev/null 2>&1 &
exit 143
WRAP
chmod +x "$out/fake-bin/xargs"
rm -f "$out/xargs-late-child"
rc=0
env PATH="$out/fake-bin:$PATH" BMAKE="$out/bmake" MAKECONF="$out/mk.conf" PKGSRCDIR="$out/tree" \
    CROSS_BULK_JOBS=1 CROSS_BULK_SHELL="$selected_shell" \
    "$selected_shell" "$ports/scripts/cross-bulk.sh" order "$out/roots" "$out/state" \
    > "$out/xargs-signal.log" 2>&1 || rc=$?
[ "$rc" -eq 143 ] || fail "interrupted xargs status was lost: $rc"
[ -d "$out/state/build.lock" ] || fail 'interrupted xargs released the lock before descendants were known drained'
i=0
while [ ! -e "$out/xargs-late-child" ] && [ "$i" -lt 100 ]; do
    sleep 0.05
    i=$((i + 1))
done
[ -e "$out/xargs-late-child" ] || fail 'interrupted-xargs child did not finish'
rm -rf "$out/state/build.lock"

# The successful selected path resolves only its requested closure.
env BMAKE="$out/bmake" MAKECONF="$out/mk.conf" PKGSRCDIR="$out/tree" \
    CROSS_BULK_SHELL="$selected_shell" \
    "$selected_shell" "$ports/scripts/cross-bulk.sh" selected-order "$out/roots" "$out/state" \
    > "$out/selected-order.log" 2>&1 || fail "selected-order failed: $(cat "$out/selected-order.log")"
grep -q '^Target: NetBSD aarch64 (aarch64--netbsd)$' "$out/selected-order.log" || fail 'selected-order omitted target identity'
grep -q '^Selected roots: 1$' "$out/selected-order.log" || fail 'selected-order reported the wrong root count'
grep -q '^Dependency closure: 2 packages (2 target, 0 native)$' "$out/selected-order.log" || fail 'selected-order reported the wrong closure'

env BMAKE="$out/bmake" MAKECONF="$out/mk.conf" PKGSRCDIR="$out/tree" \
    CROSS_BULK_SHELL="$selected_shell" \
    CROSS_BULK_CPUS=2 CROSS_BULK_JOBS=2 \
    "$selected_shell" "$ports/scripts/cross-bulk.sh" selected-build "$out/roots" "$out/state" \
    > "$out/selected.log" 2>&1 || fail "selected-build failed: $(cat "$out/selected.log")"
grep -qx 'cat/dep' "$out/state/order" || fail 'selected order omitted transitive dependency'
grep -qx 'cat/app' "$out/state/order" || fail 'selected order omitted requested package'
[ "$(wc -l < "$out/state/order" | tr -d ' ')" -eq 2 ] || fail 'selected order included packages outside the closure'
[ -s "$out/targets" ] || fail 'selected build did not build its new closure'
target_count=$(wc -l < "$out/targets" | tr -d ' ')
[ "$target_count" -gt 0 ] || fail 'selected build did not run package targets'
[ ! -s "$out/missing-build-lock" ] || fail "worker EXIT trap released the parent lock: $(cat "$out/missing-build-lock")"
grep -q '^yes show-vars ' "$out/cache-calls" || fail 'order did not use its PBULK options cache'
grep -q '^no show-vars ' "$out/cache-calls" || fail 'build did not query installed package metadata outside the order cache'

# The same selected closure is planned again, but accepted packages stay done.
env BMAKE="$out/bmake" MAKECONF="$out/mk.conf" PKGSRCDIR="$out/tree" \
    CROSS_BULK_SHELL="$selected_shell" \
    CROSS_BULK_CPUS=2 CROSS_BULK_JOBS=1 \
    sh "$ports/scripts/cross-bulk.sh" selected-build "$out/roots" "$out/state" \
    > "$out/selected-again.log" 2>&1 || fail "second selected-build failed: $(cat "$out/selected-again.log")"
[ "$(wc -l < "$out/targets" | tr -d ' ')" -eq "$target_count" ] ||
    fail 'second selected build rebuilt accepted packages'
[ ! -e "$out/state/build.lock" ] || fail 'selected build left its state lock'

# If dependency ordering fails, selected-build must stop before package targets.
: > "$out/targets"
printf '%s\n' cat/fail > "$out/roots"
rc=0
env BMAKE="$out/bmake" MAKECONF="$out/mk.conf" PKGSRCDIR="$out/tree" \
    CROSS_BULK_SHELL="$selected_shell" \
    CROSS_BULK_CPUS=2 CROSS_BULK_JOBS=1 \
    sh "$ports/scripts/cross-bulk.sh" selected-build "$out/roots" "$out/state" \
    > "$out/order-failure.log" 2>&1 || rc=$?
[ "$rc" -ne 0 ] || fail 'selected-build ignored dependency-order failure'
[ ! -s "$out/targets" ] || fail 'selected-build started package work after order failure'
[ ! -e "$out/state/build.lock" ] || fail 'failed selected-build left its state lock'
echo 'PASS: order/selected-build lock refusal, selected dependency closure, accepted package reuse, and fail-closed ordering'

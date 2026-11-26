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
host_python=${CROSS_BULK_TEST_PYTHON:-$(command -v python3)}
: "${CROSS_BULK_TEST_SDK_SOURCE:?Set CROSS_BULK_TEST_SDK_SOURCE to the selected SDK source}"
mkdir -p "$out/tree/pkgtools/pkg_install" "$out/tree/cat/app" \
    "$out/tree/cat/dep" "$out/tree/cat/fail" "$out/packages/All" \
    "$out/native-db" "$out/target-db" "$out/state/logs" "$out/sdk/scripts"
ln -s "$CROSS_BULK_TEST_SDK_SOURCE/src" "$out/sdk/src"
ln -s "$CROSS_BULK_TEST_SDK_SOURCE/scripts/prefix-lock.py" "$out/sdk/scripts/prefix-lock.py"
# Use real stage locking and process supervision. Only CPU capacity is fixed.
printf 'print(2)\n' > "$out/sdk/scripts/resolve-jobs.py"
: > "$out/mk.conf"
for p in app dep fail; do : > "$out/tree/cat/$p/Makefile"; done
: > "$out/tree/pkgtools/pkg_install/Makefile"
mkdir -p "$out/tree/mk"
cat > "$out/pkg_info" <<'WRAP'
#!/bin/sh
db=$2
shift 2
case "$1" in
    -e) [ -f "$db/$2/+CONTENTS" ] || exit 1; echo "$2" ;;
    -q) case "$3" in /*) cat "$3" ;; *) cat "$db/$3/+CONTENTS" ;; esac ;;
    *) exit 1 ;;
esac
WRAP
cat > "$out/bmake" <<WRAP
#!/bin/sh
out=$out
if [ "\${CHECK_AWK_FALLBACK:-no}" = yes ]; then
    printf '%s\\n' "\${CROSS_BULK_ENV_IDENTITY:-}" > "$out/awk-env-identity"
    exit 1
fi
dir= target= varname= varnames= cross=no
cache=no fresh_makevars=no
for arg do
    case "\$arg" in
        PBULK_CACHE_DIRECTORY=*) cache=yes ;;
        _MAKEVARS_MK=defined) fresh_makevars=yes ;;
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
        _DEPENDS_FILE=*) depfile=\${1#*=}; shift ;;
        _RDEPENDS_FILE=*) resolved=\${1#*=}; shift ;;
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
            EMBERBSD_HOST_PYTHON) echo "$host_python" ;;
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
                EMBERBSD_HOST_PYTHON) echo "$host_python" ;;
                EMBERBSD_SDK_SOURCE) echo "$out/sdk" ;;
                PKG_SKIP_REASON) echo ;;
                DEPENDS) if [ "\$pkg" = app ]; then echo 'dep>=1:../../cat/dep'; else echo ; fi ;;
                BUILD_DEPENDS|TOOL_DEPENDS|BOOTSTRAP_DEPENDS) echo ;;
                PKGBASE) echo "\$pkg" ;;
                PKGNAME) echo "\$pkg-1.0" ;;
                PKGVERSION_NOREV) echo 1.0 ;;
                PKGFILE) echo "$out/packages/All/\$pkg-1.0.tgz" ;;
                WRKDIR) echo "$out/work/cat/\$pkg" ;;
                WRKOBJDIR) echo "$out/work" ;;
                .MAKE.MAKEFILES) echo "\$dir/Makefile" ;;
                .CURDIR) echo "\$dir" ;;
                *) echo ;;
            esac
        done ;;
    *.rdepends|*.depends)
        : > "\$depfile"
        : > "\$resolved"
        if [ "\$pkg" = app ]; then
            provider=dep
            if [ -f "$out/new-provider" ] && { [ "\$fresh_makevars" = yes ] || [ ! -f "$out/work/cat/app/.configure_makevars.mk" ]; }; then
                provider=replacement
            fi
            printf 'full\t%s>=1\t../../cat/%s\n' "\$provider" "\$provider" > "\$depfile"
            printf 'full\t%s>=1\t%s-1.0\n' "\$provider" "\$provider" > "\$resolved"
        fi ;;
    clean) rm -rf "$out/work/cat/\$pkg"; echo "TARGET clean" >> "$out/targets" ;;
    package|replace) echo "TARGET \$target" >> "$out/targets" ;;
    package-install)
        [ -d "$out/state/build.lock" ] || echo "\$pkg" >> "$out/missing-build-lock"
        echo "TARGET \$target" >> "$out/targets"
        work="$out/work/cat/\$pkg"
        mkdir -p "\$work" "$out/packages/All" "$out/target-db/\$pkg-1.0"
        for phase in extract configure build install package; do echo "\$pkg-1.0" > "\$work/.\${phase}_done"; done
        : > "\$work/.depends"
        : > "\$work/.rdepends"
        printf '@name %s-1.0\n' "\$pkg" > "$out/packages/All/\$pkg-1.0.tgz"
        if [ "\$pkg" = app ]; then
            printf 'full\tdep>=1\t../../cat/dep\n' > "\$work/.depends"
            printf 'full\tdep>=1\tdep-1.0\n' > "\$work/.rdepends"
            echo '@pkgdep dep>=1' >> "$out/packages/All/\$pkg-1.0.tgz"
        fi
        cp "$out/packages/All/\$pkg-1.0.tgz" "$out/target-db/\$pkg-1.0/+CONTENTS"
        echo OPSYS=NetBSD > "$out/target-db/\$pkg-1.0/+BUILD_INFO" ;;
    *) echo "unknown target: \$target" >&2; exit 2 ;;
esac
WRAP
chmod +x "$out/pkg_info" "$out/bmake"
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

# A curated native prefix can expose BSD nawk without an awk basename. The
# controller must compute the environment identity through that selected
# implementation, without depending on another PATH directory.
mkdir -p "$out/no-awk-bin"
"$host_python" - "$out/no-awk-bin" <<'PY'
from pathlib import Path
from shutil import which
import sys

for tool in "env sort shasum rm mkdir rmdir printf tsort".split():
    executable = which(tool)
    if executable is None:
        sys.exit(f"test host lacks {tool}")
    (Path(sys.argv[1]) / tool).symlink_to(Path(executable).absolute())
PY
nawk_path=$(command -v nawk || command -v awk) || fail 'test host lacks an awk-compatible implementation'
ln -s "$nawk_path" "$out/no-awk-bin/nawk"
[ ! -e "$out/no-awk-bin/awk" ] || fail 'curated PATH unexpectedly contains awk'
rm -f "$out/awk-env-identity"
rc=0
env PATH="$out/no-awk-bin" CHECK_AWK_FALLBACK=yes \
    BMAKE="$out/bmake" MAKECONF="$out/mk.conf" PKGSRCDIR="$out/tree" \
    CROSS_BULK_SHELL="$selected_shell" \
    "$selected_shell" "$ports/scripts/cross-bulk.sh" selected-order "$out/roots" "$out/state" \
    > "$out/nawk-fallback.log" 2>&1 || rc=$?
[ "$rc" -eq 2 ] || fail "selected nawk probe exited $rc instead of reaching the deliberate bmake failure"
awk_identity=$(cat "$out/awk-env-identity")
[ "${#awk_identity}" -eq 64 ] || fail 'selected nawk did not produce the environment digest'
case "$awk_identity" in *[!0-9a-f]*) fail 'selected nawk produced a malformed environment digest' ;; esac
grep -q 'native host prefix selection failed verification' "$out/nawk-fallback.log" ||
    fail 'selected nawk probe did not reach the deliberate bmake failure'
[ ! -e "$out/state/build.lock" ] || fail 'nawk probe left its state lock'

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
    "$selected_shell" "$ports/scripts/cross-bulk.sh" selected-build "$out/roots" "$out/state" \
    > "$out/selected-again.log" 2>&1 || fail "second selected-build failed: $(cat "$out/selected-again.log")"
[ "$(wc -l < "$out/targets" | tr -d ' ')" -eq "$target_count" ] ||
    fail 'second selected build rebuilt accepted packages'
[ ! -e "$out/state/build.lock" ] || fail 'selected build left its state lock'

# A retained pre-change provider list cannot vouch for existing objects.
# An explicit, scoped clean and ordinary compile establishes both receipts.
legacy_app=$out/work/cat/app
rm "$legacy_app/.cross-bulk-providers" "$out/state/source-inputs/cat_app"
printf 'pre-change object\n' > "$legacy_app/retained.o"
build_existing_order()
{
    env BMAKE="$out/bmake" MAKECONF="$out/mk.conf" PKGSRCDIR="$out/tree" \
        CROSS_BULK_SHELL="$selected_shell" CROSS_BULK_CPUS=2 CROSS_BULK_JOBS=1 \
        "$selected_shell" "$ports/scripts/cross-bulk.sh" build "$out/state/order" "$out/state" \
        > "$out/legacy.log" 2>&1
}
if build_existing_order; then fail 'unproven legacy objects were reused'; fi
grep -q 'kept stage has no evidence' "$out/state/logs/cat_app.worker.log" || fail 'legacy refusal lost its reason'
[ "$(cat "$legacy_app/retained.o")" = 'pre-change object' ] || fail 'legacy refusal removed objects'
"$out/bmake" -C "$out/tree/cat/app" clean
: > "$out/targets"
build_existing_order || fail "ordinary legacy rebuild: $(cat "$out/legacy.log")"
[ -s "$legacy_app/.cross-bulk-providers" ] && [ -s "$out/state/source-inputs/cat_app" ] ||
    fail 'ordinary rebuild did not establish provider and archive evidence'
grep -Fqx 'TARGET package-install' "$out/targets" || fail 'ordinary rebuild did not compile/package'
: > "$out/targets"
# Ordinary nodes also run with shared staging explicitly disabled. A reused
# done package keeps its WRKDIR, also when successful builds clean theirs.
: > "$legacy_app/kept"
(CROSS_BULK_SHARED_BUILD=no CROSS_BULK_CLEAN_SUCCESS=yes build_existing_order) ||
    fail "post-migration reuse: $(cat "$out/legacy.log")"
[ ! -s "$out/targets" ] || fail 'post-migration run repeated package work'
[ -f "$legacy_app/kept" ] || fail 'cleanup removed the WRKDIR of a reused package'

# The kept phase cache can still name the old provider after selection changed.
# Both the completed archive and the retained objects must use a fresh resolver.
mkdir "$out/target-db/replacement-1.0"
echo '@name replacement-1.0' > "$out/target-db/replacement-1.0/+CONTENTS"
echo 'OPSYS=NetBSD' > "$out/target-db/replacement-1.0/+BUILD_INFO"
: > "$legacy_app/.configure_makevars.mk"
: > "$out/new-provider"
printf 'keep the old object\n' > "$legacy_app/retained.o"
if build_existing_order; then fail 'old phase provider concealed a changed source dependency'; fi
grep -q 'dependency metadata changed' "$out/state/logs/cat_app.worker.log" || fail 'missing changed-provider refusal'
[ ! -s "$out/targets" ] && [ -s "$legacy_app/retained.o" ] || fail 'changed provider reused or cleaned the old objects'
rm "$out/new-provider"

# If dependency ordering fails, selected-build must stop before package targets.
: > "$out/targets"
printf '%s\n' cat/fail > "$out/roots"
rc=0
env BMAKE="$out/bmake" MAKECONF="$out/mk.conf" PKGSRCDIR="$out/tree" \
    CROSS_BULK_SHELL="$selected_shell" \
    CROSS_BULK_CPUS=2 CROSS_BULK_JOBS=1 \
    "$selected_shell" "$ports/scripts/cross-bulk.sh" selected-build "$out/roots" "$out/state" \
    > "$out/order-failure.log" 2>&1 || rc=$?
[ "$rc" -ne 0 ] || fail 'selected-build ignored dependency-order failure'
[ ! -s "$out/targets" ] || fail 'selected-build started package work after order failure'
[ ! -e "$out/state/build.lock" ] || fail 'failed selected-build left its state lock'
echo 'PASS: order/selected-build lock refusal, selected dependency closure, accepted package reuse, and fail-closed ordering'

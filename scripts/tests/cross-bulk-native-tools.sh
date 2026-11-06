#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). The native tools of a cross bulk are graph
# nodes of their own, and only installs take a lock. With a recording bmake
# on a small tree: order adds DEPENDS and BUILD_DEPENDS as target nodes,
# TOOL_DEPENDS and BOOTSTRAP_DEPENDS as native nodes, and native transitive
# dependencies as PKGPATH@native;
# build installs each native tool once, before its users, with the target
# settings only for the tools of target packages, skips a tool the native
# prefix has, never builds a dependency in a package's depends step, lets
# other packages build and install while one package spends long in its
# depends step, and never runs two installs into one package database.
# A tool the native prefix has is a leaf, so the cycle between it and a
# tool it needs (n/old and n/cyc) does not reach the graph; a cycle among
# tools to build is refused.
# Usage: cross-bulk-native-tools.sh NEW_OUTPUT
set -eu
[ "$#" = 1 ] || { echo 'Usage: cross-bulk-native-tools.sh NEW_OUTPUT' >&2; exit 2; }
out=$1
case "$out" in /*) ;; *) echo 'NEW_OUTPUT must be absolute' >&2; exit 2 ;; esac
case "$out" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2 ;; esac
[ ! -e "$out" ] || exit 2
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
mkdir -p "$out/tree" "$out/packages/All" "$out/work" "$out/target-db" "$out/native-db"
: > "$out/errors"
# Each row gives DIR, DEPENDS, BUILD_DEPENDS and TOOL_DEPENDS. t/ are target
# packages and n/ native tools. Every target package needs n/old to bootstrap;
# the native prefix has it. n/old and n/cyc need each other, as the bootstrap
# tools of pkgsrc do.
while read -r dir deps builddeps tools; do
    mkdir -p "$out/tree/$dir"
    [ "$deps" = - ] || echo "$deps" | tr , '\n' > "$out/tree/$dir/deps"
    [ "$builddeps" = - ] || echo "$builddeps" | tr , '\n' > "$out/tree/$dir/builddeps"
    [ "$tools" = - ] || echo "$tools" | tr , '\n' > "$out/tree/$dir/tools"
done <<'TREE'
t/a flang-rt b gen,dispatch
t/b - - -
t/c - - -
t/d a - -
t/flang-rt - - flang
n/gen - - base
n/base - - -
n/flang - - -
n/dispatch - - -
n/old - - cyc
n/cyc - - old
TREE
printf '%s\n' flang-rt > "$out/tree/n/dispatch/cross-target-deps"
: > "$out/native-db/old"
cat > "$out/pkg_add" <<WRAP
#!/bin/sh
[ "\$1" = -K ] || { echo "pkg_add without -K: \$*" >> $out/errors; exit 1; }
db=\$(basename "\$2")
mkdir $out/adding-\$db 2> /dev/null || echo "OVERLAP \$db \$3" >> $out/errors
sleep 0.5
rmdir $out/adding-\$db
: > "\$2/\$3"
WRAP
# The database names packages by PKGBASE; each is at the tree's version
# 1.0, so it satisfies BASE>=1.0 (scripts/tests/cross-bulk-native-version.sh
# checks older and newer versions).
cat > "$out/pkg_info" <<WRAP
#!/bin/sh
[ "\$1" = -K ] && [ "\$3" = -e ] && [ -e "\$2/\${4%%>=*}" ]
WRAP
cat > "$out/bmake" <<WRAP
#!/bin/sh
out=$out
echo "\$*" >> \$out/calls
dir= target= varname= varnames= add= native= settings=
while [ "\$#" -gt 0 ]; do
    case "\$1" in
        -C) dir=\$2; shift 2 ;;
        VARNAME=*) varname=\${1#VARNAME=}; shift ;;
        VARNAMES=*) varnames=\${1#VARNAMES=}; shift ;;
        NATIVE_PKG_ADD_CMD=*) add=\${1#NATIVE_PKG_ADD_CMD=}; shift ;;
        USE_CROSS_COMPILE=no) native=1; shift ;;
        TARGET_OPSYS=*) settings=\$1; shift ;;
        *=*) shift ;;
        *) target=\$1; shift ;;
    esac
done
pkg=\${dir##*/}
kind=\$(basename "\$(dirname "\$dir")")
needs()
{
    for tool in \$(cat \$dir/tools 2> /dev/null); do
        [ -e \$out/native-db/\$tool ] || echo "ORDER \$pkg before native \$tool" >> \$out/errors
    done
    for dep in \$(cat \$dir/deps 2> /dev/null); do
        [ -e \$out/target-db/\$dep ] || echo "ORDER \$pkg before \$dep" >> \$out/errors
    done
    for dep in \$(cat \$dir/builddeps 2> /dev/null); do
        [ -e \$out/target-db/\$dep ] || echo "ORDER \$pkg before build dependency \$dep" >> \$out/errors
    done
    if [ "\$kind" = n ]; then
        for dep in \$(cat \$dir/cross-target-deps 2> /dev/null); do
            [ -e \$out/target-db/\$dep ] || echo "ORDER \$pkg before target-fed dependency \$dep" >> \$out/errors
        done
    fi
}
work()
{
    [ ! -f \$out/work/\$kind-\$pkg.built ] || return 0
    needs
    sleep \${FAKE_SLEEP:-1}
    : > \$out/work/\$kind-\$pkg.built
}
list()
{
    for x in \$(cat \$dir/\$1 2> /dev/null); do
        if [ "\$pkg" = a ] && [ "\$1" = tools ] && [ "\$x" = mesa-generators ]; then
            printf '%s ' "\$x>=1:../\$x"
        else
            printf '%s ' "\$x>=1:../../\$2/\$x"
        fi
    done
    echo
}
case "\$target" in
    show-var)
        case "\$varname" in
            EMBERBSD_NATIVE_TOOLSET_VERIFIED) echo fake ;;
            PACKAGES) echo \$out/packages ;;
            NATIVE_PKG_ADD_CMD) echo \$out/pkg_add ;;
            PKG_INFO) echo "\$out/pkg_info -K \$out/native-db" ;;
            CROSSTARGETSETTINGS) echo 'TARGET_OPSYS=NetBSD TARGET_MACHINE_ARCH=aarch64' ;;
            *) echo ;;
        esac ;;
    show-vars)
        for v in \$varnames; do
            case "\$v" in
                PKGNAME) echo "\$pkg-1.0" ;;
                PKGBASE) echo "\$pkg" ;;
                PKGFILE) echo "\$out/packages/All/\$pkg-1.0.tgz" ;;
                WRKDIR) echo "\$out/work/\$kind-\$pkg" ;;
                DEPENDS) list deps t ;;
                BUILD_DEPENDS) list builddeps t ;;
                TOOL_DEPENDS) list tools n ;;
                BOOTSTRAP_DEPENDS) [ -n "\$native" ] && echo || echo 'old>=1:../../n/old' ;;
                CROSS_TARGET_DEPENDS) [ -f "\$dir/cross-target-deps" ] && echo 'flang-rt>=1:../../t/flang-rt' || echo ;;
                *) echo ;;
            esac
        done ;;
    clean) rm -f \$out/work/\$kind-\$pkg.built ;;
    depends) needs ;;
    package) work ;;
    package-install)
        needs
        if [ "\$pkg" = b ]; then
            sleep 6
            [ -e \$out/target-db/c ] || echo 'WAIT c was not installed during the long depends step of b' >> \$out/errors
        fi
        work; \$add -K \$out/target-db \$pkg; : > \$out/packages/All/\$pkg-1.0.tgz ;;
    install)
        [ -n "\$native" ] || { echo "target install of \$pkg" >> \$out/errors; exit 1; }
        echo "\$pkg \${settings:-native}" >> \$out/native-builds
        work; \$add -K \$out/native-db \$pkg ;;
    *) echo "UNKNOWN \$target" >> \$out/errors; exit 1 ;;
esac
WRAP
chmod +x "$out/bmake" "$out/pkg_add" "$out/pkg_info"
fail() { echo "FAIL: $*" >&2; exit 1; }
bulk()
{
    BMAKE=$ports/scripts/tests/cross-bulk-bmake-proxy.sh CROSS_BULK_TEST_REAL_BMAKE=$out/bmake \
        MAKECONF=$out/mk.conf PKGSRCDIR=$out/tree CROSS_BULK_CPUS=8 CROSS_BULK_JOBS=4 \
        sh "$ports/scripts/cross-bulk.sh" "$1" "$out/list" "$out/$2" > "$out/$1.log" 2>&1 ||
        fail "$1: $(cat "$out/$1.log")"
}
before() { [ "$(grep -nFx "$1" "$2" | cut -d : -f 1)" -lt "$(grep -nFx "$3" "$2" | cut -d : -f 1)" ]; }

printf '%s\n' t/b t/c t/d > "$out/list"
mkdir "$out/state"
bulk order state
for edge in 'n/gen@native t/a' 'n/dispatch@native t/a' 'n/base@native n/gen@native' \
    'n/old@native t/a' 'n/old@native t/c' 'n/flang@native t/flang-rt' \
    't/flang-rt n/dispatch@native' 't/a t/d' 't/b t/a'; do
    grep -qFx "$edge" "$out/state/edges" || fail "order has no edge $edge"
done
grep -q '^n/base@native n/old@native$' "$out/state/edges" && fail 'a native node got a target bootstrap'
grep -q '^n/flang-rt@native ' "$out/state/edges" && fail 'target Flang-RT became a host package edge'
before n/gen@native "$out/state/order" t/a || fail 'n/gen@native is not ordered before t/a'
before n/flang@native "$out/state/order" t/flang-rt || fail 'native Flang is not ordered before target Flang-RT'
before t/flang-rt "$out/state/order" n/dispatch@native || fail 'target Flang-RT is not ordered before the native dispatcher'
before n/dispatch@native "$out/state/order" t/a || fail 'the native dispatcher is not ordered before its target consumer'
before n/base@native "$out/state/order" n/gen@native || fail 'n/base@native is not ordered before n/gen@native'
grep -q 'n/cyc' "$out/state/edges" && fail 'the installed n/old@native was asked for its tools'

# Same-category pkgsrc dependencies are commonly written as ../sibling.
# Exercise that path in an isolated second order so the build fixture's
# existing golden package list remains unchanged.
mkdir -p "$out/tree/t/mesa-generators" "$out/state-sibling"
echo mesa-generators >> "$out/tree/t/a/tools"
bulk order state-sibling
grep -qFx 't/mesa-generators@native t/a' "$out/state-sibling/edges" ||
	fail 'same-category sibling TOOL_DEPENDS was not resolved'
before t/mesa-generators@native "$out/state-sibling/order" t/a ||
	fail 'same-category sibling TOOL_DEPENDS is not ordered before its consumer'
sed '/^mesa-generators$/d' "$out/tree/t/a/tools" > "$out/tree/t/a/tools.tmp"
mv "$out/tree/t/a/tools.tmp" "$out/tree/t/a/tools"
if [ "${CROSS_BULK_TEST_ORDER_ONLY:-no}" = yes ]; then
	echo 'PASS: native TOOL_DEPENDS graph order, including sibling package paths'
	exit 0
fi

bulk build state
[ ! -s "$out/errors" ] || fail "$(cat "$out/errors")"
[ "$(cut -d ' ' -f 1 "$out/state/done" | sort | tr '\n' ' ')" = 'n/base@native n/dispatch@native n/flang@native n/gen@native t/a t/b t/c t/d t/flang-rt ' ] ||
    fail "done: $(cat "$out/state/done")"
[ ! -s "$out/state/failed" ] && [ ! -s "$out/state/blocked" ] || fail "failed or blocked: $(cat "$out/state/failed" "$out/state/blocked")"
[ "$(sort "$out/native-builds" | tr '\n' ' ')" = 'base native dispatch TARGET_OPSYS=NetBSD flang TARGET_OPSYS=NetBSD gen TARGET_OPSYS=NetBSD ' ] ||
    fail "native builds: $(cat "$out/native-builds")"
grep -q ' n/old' "$out/state/progress" && fail 'the installed native tool n/old was built again'
[ "$(ls "$out/target-db" | tr '\n' ' ')" = 'a b c d flang-rt ' ] || fail "target installs: $(ls "$out/target-db")"
# A current dispatcher is already installed and does not need its build-only
# target runtime edge.
: > "$out/native-db/dispatch-1.0"
mkdir "$out/state-current"
bulk order state-current
grep -q '^t/flang-rt n/dispatch@native$' "$out/state-current/edges" &&
    fail 'an installed dispatcher retained its build-only target runtime edge'
# A cycle among tools that the native prefix lacks is refused.
mkdir -p "$out/tree/t/e" "$out/tree/n/x" "$out/tree/n/y" "$out/state2"
echo x > "$out/tree/t/e/tools"
echo y > "$out/tree/n/x/tools"
echo x > "$out/tree/n/y/tools"
echo t/e > "$out/list2"
if BMAKE=$ports/scripts/tests/cross-bulk-bmake-proxy.sh CROSS_BULK_TEST_REAL_BMAKE=$out/bmake \
    MAKECONF=$out/mk.conf PKGSRCDIR=$out/tree CROSS_BULK_CPUS=8 \
    sh "$ports/scripts/cross-bulk.sh" order "$out/list2" "$out/state2" > "$out/cycle.log" 2>&1; then
    fail 'order accepted a cycle among tools to build'
fi
grep -q 'cycle' "$out/cycle.log" || fail "cycle refusal: $(cat "$out/cycle.log")"
[ ! -e "$out/state2/order" ] || fail 'order wrote an order with a cycle'

# A target and native node can share one PKGBASE. Their package options are
# role-specific, so order must scope pkgsrc's shared cache by the existing
# target/@native node role. Independent frontier queries must stay bounded,
# preserve the serial graph, and retain per-node query failures.
mkdir -p "$out/order-tree/pkgtools/pkg_install" "$out/order-tree/t/app" \
    "$out/order-tree/t/shared" "$out/order-tree/t/skipped" "$out/order-tree/n/shared" "$out/order-tree/a_b/pkg" \
    "$out/order-tree/a/b_pkg" "$out/order-tree/a/leaf1" "$out/order-tree/a/leaf2" \
    "$out/order-tree/db-target/provider-1.0" "$out/order-tree/db-native/provider-1.0" \
    "$out/order-tree/mk" \
    "$out/order-cache"
: > "$out/order-cache/errors"
: > "$out/order-tree/mk.conf"
: > "$out/order-tree/pkgtools/pkg_install/Makefile"
for dir in t/app t/shared t/skipped n/shared a_b/pkg a/b_pkg a/leaf1 a/leaf2; do
    : > "$out/order-tree/$dir/Makefile"
done
printf '%s\n' 'PKG_OPTIONS=small' > "$out/order-tree/db-native/provider-1.0/+BUILD_INFO"
printf '%s\n' t/app t/skipped > "$out/order-list"
printf '%s\n' 'shared>=1.0:../../t/shared pkg>=1.0:../../a_b/pkg pkg>=1.0:../../a/b_pkg' > "$out/order-tree/t/app/deps.list"
cat > "$out/order-bmake" <<WRAP
#!/bin/sh
out=$out
dir= target= varname= varnames= native= cache=
while [ "\$#" -gt 0 ]; do
    case "\$1" in
        -C) dir=\$2; shift 2 ;;
        VARNAME=*) varname=\${1#VARNAME=}; shift ;;
        VARNAMES=*) varnames=\${1#VARNAMES=}; shift ;;
        PBULK_CACHE_DIRECTORY=*) cache=\${1#PBULK_CACHE_DIRECTORY=}; shift ;;
        USE_CROSS_COMPILE=no) native=yes; shift ;;
        *=*) shift ;;
        *) target=\$1; shift ;;
    esac
done
pkg=\${dir##*/}
kind=\$(basename "\$(dirname "\$dir")")
case "\$target" in
    show-var)
        case "\$varname" in
            EMBERBSD_NATIVE_TOOLSET_VERIFIED) echo fake ;;
            PKG_INFO) echo /usr/bin/false ;;
            _PKG_DBDIR) [ -z "\$native" ] && echo $out/order-tree/db-target || echo $out/order-tree/db-native ;;
            _HOST_PKG_DBDIR) echo $out/order-tree/db-native ;;
            .MAKE.MAKEFILES) echo $out/order-tree/pkgtools/pkg_install/Makefile ;;
            *) echo ;;
        esac ;;
    show-vars)
        case " \$varnames " in
            *" PKG_SKIP_REASON "*)
                role=target; [ -z "\$native" ] || role=native
                echo "\$kind/\$pkg \$role" >> $out/order-cache/dependency-queries
                echo "fixture-warning \$kind/\$pkg" >&2
                while ! mkdir $out/order-cache/query-lock 2> /dev/null; do sleep 0.01; done
                active=\$(cat $out/order-cache/active 2> /dev/null || echo 0)
                active=\$((active + 1)); echo \$active > $out/order-cache/active
                max=\$(cat $out/order-cache/max 2> /dev/null || echo 0)
                [ \$active -le \$max ] || echo \$active > $out/order-cache/max
                rmdir $out/order-cache/query-lock
                sleep 0.25
                if [ "\$pkg" = shared ] && [ -n "\$cache" ]; then
                    role=target; [ -z "\$native" ] || role=native
                    while ! mkdir $out/order-cache/options-lock 2> /dev/null; do sleep 0.01; done
                    mkdir -p "\$cache"
                    option=\$cache/build-options.shared
                    if [ -f "\$option" ]; then found=\$(cat "\$option")
                    else echo \$role > "\$option.tmp.\$\$"; mv "\$option.tmp.\$\$" "\$option"; found=\$role
                    fi
                    [ "\$found" = "\$role" ] || echo "CACHE-CONTAMINATION \$role read \$found" >> $out/order-cache/errors
                    rmdir $out/order-cache/options-lock
                fi
                if [ -f $out/order-cache/fail-\$kind-\$pkg ]; then
                    while ! mkdir $out/order-cache/query-lock 2> /dev/null; do sleep 0.01; done
                    active=\$(cat $out/order-cache/active); echo \$((active - 1)) > $out/order-cache/active
                    rmdir $out/order-cache/query-lock; exit 1
                fi
                while ! mkdir $out/order-cache/query-lock 2> /dev/null; do sleep 0.01; done
                active=\$(cat $out/order-cache/active); echo \$((active - 1)) > $out/order-cache/active
                rmdir $out/order-cache/query-lock ;;
        esac
        for v in \$varnames; do
            case "\$v" in
                PKG_SKIP_REASON) if [ "\$pkg" = skipped ]; then echo 'outside profile'; else echo; fi ;;
                DEPENDS)
                    case "\$kind/\$pkg" in
                        t/app)
                            if [ "\${PKG_DEFAULT_OPTIONS:-}" = large-env ]; then
                                echo 'leaf2>=1.0:../../a/leaf2'
                            elif [ -f $out/order-tree/db-target/provider-1.0/+BUILD_INFO ] &&
                                grep -q 'PKG_OPTIONS=large' $out/order-tree/db-target/provider-1.0/+BUILD_INFO; then
                                echo 'leaf2>=1.0:../../a/leaf2'
                            else
                                cat $out/order-tree/t/app/deps.list
                            fi ;;
                        a_b/pkg) echo 'leaf1>=1.0:../../a/leaf1' ;;
                        a/b_pkg) echo 'leaf2>=1.0:../../a/leaf2' ;;
                        *) echo ;;
                    esac ;;
                TOOL_DEPENDS) if [ "\$pkg" = app ]; then echo 'shared>=1.0:../../n/shared'; else echo; fi ;;
                PKGBASE) echo "\$pkg" ;;
                PKGNAME) echo "\$kind-\$pkg-1.0" ;;
                .MAKE.MAKEFILES) printf 'Makefile %s' "$out/order-tree/mk.conf"; [ "\$kind/\$pkg" != t/app ] || printf ' deps.list'; [ -z "\$cache" ] || printf ' %s/build-options.shared' "\$cache"; echo ;;
                .CURDIR) echo "$out/order-tree/\$kind/\$pkg" ;;
                *) echo ;;
            esac
        done ;;
    *) echo "unexpected order query target: \$target" >&2; exit 2 ;;
esac
WRAP
chmod +x "$out/order-bmake"
order_run()
{
    state=$1 jobs=$2 options=${3:-} tool_path=${4:-$PATH}
    mkdir -p "$out/$state"
    PATH=$tool_path PKG_DEFAULT_OPTIONS=$options BMAKE=$out/order-bmake MAKECONF=$out/order-tree/mk.conf \
        PKGSRCDIR=$out/order-tree CROSS_BULK_JOBS=$jobs \
        sh "$ports/scripts/cross-bulk.sh" order "$out/order-list" "$out/$state" \
        > "$out/$state.log" 2>&1
}
order_run order-serial 1 || fail "serial cache fixture: $(cat "$out/order-serial.log")"
if grep -q CACHE-CONTAMINATION "$out/order-cache/errors"; then
    fail 'native and target package options shared one PKGBASE cache entry'
fi
[ -f "$out/order-serial/build-options/native/build-options.shared" ] || fail 'native options cache was not role-scoped'
[ -f "$out/order-serial/build-options/target/build-options.shared" ] || fail 'target options cache was not role-scoped'
query_count=$(wc -l < "$out/order-cache/dependency-queries" | tr -d ' ')
order_run order-serial 1 || fail "unchanged order cache fixture: $(cat "$out/order-serial.log")"
[ "$(wc -l < "$out/order-cache/dependency-queries" | tr -d ' ')" = "$query_count" ] ||
    fail 'unchanged order repeated dependency bmake queries'
for name in order edges skipped; do cp "$out/order-serial/$name" "$out/expected-$name"; done
cp "$out/order-serial/logs/order.err" "$out/expected-order.err"
printf '%s\n' 'leaf1>=1.0:../../a/leaf1' > "$out/order-tree/t/app/deps.list"
order_run order-serial 1 || fail "recipe change order cache fixture: $(cat "$out/order-serial.log")"
grep -qFx 'a/leaf1 t/app' "$out/order-serial/edges" || fail 'recipe edit did not change dependency graph'
query_count=$(wc -l < "$out/order-cache/dependency-queries" | tr -d ' ')
printf '%s\n' 'PKG_OPTIONS=large' > "$out/order-tree/db-target/provider-1.0/+BUILD_INFO"
order_run order-serial 1 || fail "pkgdb change order cache fixture: $(cat "$out/order-serial.log")"
grep -qFx 'a/leaf2 t/app' "$out/order-serial/edges" || fail 'pkgdb option change did not change dependency graph'
[ "$(wc -l < "$out/order-cache/dependency-queries" | tr -d ' ')" -gt "$query_count" ] ||
    fail 'pkgdb install did not invalidate dependency bmake queries'
query_count=$(wc -l < "$out/order-cache/dependency-queries" | tr -d ' ')
printf '%s\n' 'PKG_OPTIONS=small' > "$out/order-tree/db-target/provider-1.0/+BUILD_INFO"
order_run order-serial 1 || fail "pkgdb metadata update fixture: $(cat "$out/order-serial.log")"
[ "$(wc -l < "$out/order-cache/dependency-queries" | tr -d ' ')" -gt "$query_count" ] ||
    fail 'pkgdb metadata update did not invalidate dependency bmake queries'
query_count=$(wc -l < "$out/order-cache/dependency-queries" | tr -d ' ')
rm "$out/order-tree/db-target/provider-1.0/+BUILD_INFO"
order_run order-serial 1 || fail "pkgdb removal fixture: $(cat "$out/order-serial.log")"
[ "$(wc -l < "$out/order-cache/dependency-queries" | tr -d ' ')" -gt "$query_count" ] ||
    fail 'pkgdb removal did not invalidate dependency bmake queries'
query_count=$(wc -l < "$out/order-cache/dependency-queries" | tr -d ' ')
order_run order-serial 1 large-env || fail "environment option order fixture: $(cat "$out/order-serial.log")"
grep -qFx 'a/leaf2 t/app' "$out/order-serial/edges" || fail 'environment option change did not change dependency graph'
[ "$(wc -l < "$out/order-cache/dependency-queries" | tr -d ' ')" -gt "$query_count" ] ||
    fail 'environment option change did not invalidate dependency bmake queries'
real_sort=$(command -v sort)
mkdir "$out/fail-env"
cat > "$out/fail-env/env" <<'WRAP'
#!/bin/sh
exit 1
WRAP
cat > "$out/fail-env/sort" <<WRAP
#!/bin/sh
[ "\$1" != -z ] || exit 1
exec "$real_sort" "\$@"
WRAP
chmod +x "$out/fail-env/env" "$out/fail-env/sort"
order_run order-env-fail 1 '' "$out/fail-env:$PATH" || fail 'order failed when environment hashing was unavailable'
[ ! -e "$out/order-env-fail/build-options" ] || fail 'failed environment hash left a reusable cache'
order_run order-sort-fail 1 '' "$out/fail-env:$PATH" || fail 'order failed when NUL sorting was unavailable'
[ ! -e "$out/order-sort-fail/build-options" ] || fail 'failed NUL sort left a reusable cache'
printf '%s\n' 'shared>=1.0:../../t/shared pkg>=1.0:../../a_b/pkg pkg>=1.0:../../a/b_pkg' > "$out/order-tree/t/app/deps.list"
echo 0 > "$out/order-cache/active"
echo 0 > "$out/order-cache/max"
order_run order-parallel 2 || fail "parallel cache fixture: $(cat "$out/order-parallel.log")"
[ -f "$out/order-parallel/build-options/native/build-options.shared" ] || fail 'parallel native cache escaped its state'
[ -f "$out/order-parallel/build-options/target/build-options.shared" ] || fail 'parallel target cache escaped its state'
for name in order edges skipped; do
    cmp -s "$out/expected-$name" "$out/order-parallel/$name" ||
        fail "parallel order changed $name"
done
grep -qFx 't/skipped outside profile' "$out/order-parallel/skipped" || fail 'parallel order lost skipped node'
grep -qFx 'a/leaf1 a_b/pkg' "$out/order-parallel/edges" || fail 'first colliding node lost its dependency'
grep -qFx 'a/leaf2 a/b_pkg' "$out/order-parallel/edges" || fail 'second colliding node lost its dependency'
max=$(cat "$out/order-cache/max")
[ "$max" = 2 ] || fail "frontier query concurrency was $max, expected bounded overlap at 2"
[ ! -s "$out/order-cache/errors" ] || fail "role cache contamination: $(cat "$out/order-cache/errors")"
cmp -s "$out/expected-order.err" "$out/order-parallel/logs/order.err" || fail 'parallel order changed query warnings'
echo 0 > "$out/order-cache/active"
echo 0 > "$out/order-cache/max"
: > "$out/order-cache/errors"
touch "$out/order-cache/fail-t-shared"
if order_run order-serial-fail 1; then fail 'serial order accepted an unreadable dependency'; fi
echo 0 > "$out/order-cache/active"
if order_run order-parallel-fail 2; then fail 'parallel order accepted an unreadable dependency'; fi
for name in order edges skipped; do
    [ ! -e "$out/order-serial-fail/$name" ] && [ ! -e "$out/order-parallel-fail/$name" ] ||
        fail "failed query published an incomplete $name"
done
cmp -s "$out/order-serial-fail/failed" "$out/order-parallel-fail/failed" ||
    fail 'parallel query failure changed the failed nodes'
grep -qFx 't/shared order' "$out/order-parallel-fail/failed" || fail 'parallel query failure was lost'
echo 'PASS: native tools are graph nodes, a long depends step blocks nobody, installs into one database never overlap, installed tools are leaves, a tool cycle is refused'

#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). The native tools of a cross bulk are graph
# nodes of their own, and only installs take a lock. With a recording bmake
# on a small tree: order adds the TOOL_DEPENDS and BOOTSTRAP_DEPENDS of the
# target packages and the dependencies of those natively (PKGPATH@native);
# tools adds the same nodes to an older order for the packages not yet done;
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
# DIR DEPENDS TOOL_DEPENDS: t/ are target packages, n/ native tools. Every
# target package needs n/old to bootstrap; the native prefix has it. n/old
# and n/cyc need each other, as the bootstrap tools of pkgsrc do.
while read -r dir deps tools; do
    mkdir -p "$out/tree/$dir"
    [ "$deps" = - ] || echo "$deps" | tr , '\n' > "$out/tree/$dir/deps"
    [ "$tools" = - ] || echo "$tools" | tr , '\n' > "$out/tree/$dir/tools"
done <<'TREE'
t/a - gen
t/b - -
t/c - -
t/d a -
n/gen - base
n/base - -
n/old - cyc
n/cyc - old
TREE
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
cat > "$out/pkg_info" <<WRAP
#!/bin/sh
[ "\$1" = -K ] && [ "\$3" = -e ] && [ -e "\$2/\$4" ]
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
    for x in \$(cat \$dir/\$1 2> /dev/null); do printf '%s ' "\$x>=1:../../\$2/\$x"; done
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
                WRKDIR) echo "\$out/work/\$kind-\$pkg" ;;
                DEPENDS) list deps t ;;
                TOOL_DEPENDS) list tools n ;;
                BOOTSTRAP_DEPENDS) [ -n "\$native" ] && echo || echo 'old>=1:../../n/old' ;;
                *) echo ;;
            esac
        done ;;
    clean) rm -f \$out/work/\$kind-\$pkg.built ;;
    depends)
        needs
        if [ "\$pkg" = b ]; then
            sleep 6
            [ -e \$out/target-db/c ] || echo 'WAIT c was not installed during the long depends step of b' >> \$out/errors
        fi ;;
    package) work ;;
    package-install) work; \$add -K \$out/target-db \$pkg; : > \$out/packages/All/\$pkg-1.0.tgz ;;
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
    BMAKE=$out/bmake MAKECONF=$out/mk.conf PKGSRCDIR=$out/tree CROSS_BULK_CPUS=8 CROSS_BULK_JOBS=4 \
        sh "$ports/scripts/cross-bulk.sh" "$1" "$out/list" "$out/$2" > "$out/$1.log" 2>&1 ||
        fail "$1: $(cat "$out/$1.log")"
}
before() { [ "$(grep -nFx "$1" "$2" | cut -d : -f 1)" -lt "$(grep -nFx "$3" "$2" | cut -d : -f 1)" ]; }

printf '%s\n' t/b t/c t/d > "$out/list"
mkdir "$out/state"
bulk order state
for edge in 'n/gen@native t/a' 'n/base@native n/gen@native' 'n/old@native t/a' 'n/old@native t/c' 't/a t/d'; do
    grep -qFx "$edge" "$out/state/edges" || fail "order has no edge $edge"
done
grep -q '^n/base@native n/old@native$' "$out/state/edges" && fail 'a native node got a target bootstrap'
before n/gen@native "$out/state/order" t/a || fail 'n/gen@native is not ordered before t/a'
before n/base@native "$out/state/order" n/gen@native || fail 'n/base@native is not ordered before n/gen@native'
grep -q 'n/cyc' "$out/state/edges" && fail 'the installed n/old@native was asked for its tools'

# tools: an order without native nodes, in which t/c is done.
mkdir "$out/old"
grep -v '@native' "$out/state/edges" > "$out/old/edges"
tsort "$out/old/edges" > "$out/old/order"
echo 't/c c-1.0 0' > "$out/old/done"
bulk tools old
grep -v '^n/old@native t/c$' "$out/state/edges" | sort > "$out/expected"
cmp -s "$out/expected" "$out/old/edges" || fail "tools edges differ: $(diff "$out/expected" "$out/old/edges")"
before n/gen@native "$out/old/order" t/a || fail 'tools did not order n/gen@native before t/a'
ls "$out/old"/order.pre-tools-* "$out/old"/edges.pre-tools-* > /dev/null || fail 'tools kept no backup'

bulk build state
[ ! -s "$out/errors" ] || fail "$(cat "$out/errors")"
[ "$(cut -d ' ' -f 1 "$out/state/done" | sort | tr '\n' ' ')" = 'n/base@native n/gen@native t/a t/b t/c t/d ' ] ||
    fail "done: $(cat "$out/state/done")"
[ ! -s "$out/state/failed" ] && [ ! -s "$out/state/blocked" ] || fail "failed or blocked: $(cat "$out/state/failed" "$out/state/blocked")"
[ "$(sort "$out/native-builds" | tr '\n' ' ')" = 'base native gen TARGET_OPSYS=NetBSD ' ] ||
    fail "native builds: $(cat "$out/native-builds")"
grep -q ' n/old' "$out/state/progress" && fail 'the installed native tool n/old was built again'
[ "$(ls "$out/target-db" | tr '\n' ' ')" = 'a b c d ' ] || fail "target installs: $(ls "$out/target-db")"
# A cycle among tools that the native prefix lacks is refused.
mkdir -p "$out/tree/t/e" "$out/tree/n/x" "$out/tree/n/y" "$out/state2"
echo x > "$out/tree/t/e/tools"
echo y > "$out/tree/n/x/tools"
echo x > "$out/tree/n/y/tools"
echo t/e > "$out/list2"
if BMAKE=$out/bmake MAKECONF=$out/mk.conf PKGSRCDIR=$out/tree CROSS_BULK_CPUS=8 \
    sh "$ports/scripts/cross-bulk.sh" order "$out/list2" "$out/state2" > "$out/cycle.log" 2>&1; then
    fail 'order accepted a cycle among tools to build'
fi
grep -q 'cycle' "$out/cycle.log" || fail "cycle refusal: $(cat "$out/cycle.log")"
[ ! -e "$out/state2/order" ] || fail 'order wrote an order with a cycle'
echo 'PASS: native tools are graph nodes, a long depends step blocks nobody, installs into one database never overlap, installed tools are leaves, a tool cycle is refused'

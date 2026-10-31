#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). scripts/cross-bulk.sh counts a native
# node as present only when the native prefix has its package at the
# version that the tree builds or newer. The native prefix of the test has
# sqlite3-3.54.1, older than the tree's sqlite3-3.54.1nb1, clang-23.1.4nb11,
# newer than the tree's clang-23.1.4nb9, and m4-1.4.21nb1, the tree's own
# version. Order must walk the tools of s/sqlite3@native and leave the
# other two as leaves; build must replace sqlite3 (pkgsrc replace keeps
# its dependents registered) and must not build clang or m4.
# Usage: cross-bulk-native-version.sh NEW_OUTPUT
set -eu
[ "$#" = 1 ] || { echo 'Usage: cross-bulk-native-version.sh NEW_OUTPUT' >&2; exit 2; }
out=$1
case "$out" in /*) ;; *) echo 'NEW_OUTPUT must be absolute' >&2; exit 2 ;; esac
case "$out" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2 ;; esac
[ ! -e "$out" ] || exit 2
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
for p in t/a s/sqlite3 c/clang m/m4 d/tclsh e/cmake; do mkdir -p "$out/tree/$p"; done
mkdir -p "$out/packages/All" "$out/work" "$out/native-db" "$out/vars"
: > "$out/native-db/sqlite3-3.54.1"
: > "$out/native-db/clang-23.1.4nb11"
: > "$out/native-db/m4-1.4.21nb1"
# vars/PKG.MODE.VARNAME holds a value; a missing file is empty.
v() { printf '%s\n' "$4" > "$out/vars/$1.$2.$3"; }
v a target PKGNAME a-1.0
v a target TOOL_DEPENDS 'sqlite3>=3.54.1nb1:../../s/sqlite3 clang>=23.1.4nb9:../../c/clang m4>=1.4:../../m/m4'
v sqlite3 native PKGNAME sqlite3-3.54.1nb1
v sqlite3 native TOOL_DEPENDS 'tclsh>=1:../../d/tclsh'
v clang native PKGNAME clang-23.1.4nb9
v clang native TOOL_DEPENDS 'cmake>=1:../../e/cmake'
v m4 native PKGNAME m4-1.4.21nb1
v m4 native TOOL_DEPENDS 'cmake>=1:../../e/cmake'
v tclsh native PKGNAME tclsh-1.0
v cmake native PKGNAME cmake-1.0
# pkg_info -K DB -e PATTERN for BASE and BASE>=VERSION patterns.
cat > "$out/pkg_info" <<'WRAP'
#!/bin/sh
db=$2 pattern=$4
case "$pattern" in
    *'>='*) base=${pattern%%>=*} want=${pattern#*>=} ;;
    *) base=$pattern want= ;;
esac
for f in "$db/$base"-[0-9]*; do
    [ -e "$f" ] || continue
    have=${f##*/}; have=${have#"$base"-}
    [ -z "$want" ] && exit 0
    [ "$(printf '%s\n%s\n' "$want" "$have" | sort -V | tail -n 1)" = "$have" ] && exit 0
done
exit 1
WRAP
cat > "$out/bmake" <<WRAP
#!/bin/sh
out=$out
dir= target= varname= varnames= mode=target
for a in "\$@"; do echo "\$a"; done | tr '\n' ' ' >> \$out/calls; echo >> \$out/calls
while [ "\$#" -gt 0 ]; do
    case "\$1" in
        -C) dir=\$2; shift 2 ;;
        VARNAME=*) varname=\${1#VARNAME=}; shift ;;
        VARNAMES=*) varnames=\${1#VARNAMES=}; shift ;;
        USE_CROSS_COMPILE=no) mode=native; shift ;;
        *=*) shift ;;
        *) target=\$1; shift ;;
    esac
done
pkg=\${dir##*/}
value() {
    case "\$1" in
        PKGBASE) sed 's/-[0-9][^-]*\$//' \$out/vars/\$pkg.\$mode.PKGNAME ;;
        WRKDIR) echo \$out/work/\$pkg/\$mode ;;
        *) cat \$out/vars/\$pkg.\$mode.\$1 2> /dev/null || echo ;;
    esac
}
case "\$target" in
    show-var)
        case "\$varname" in
            EMBERBSD_NATIVE_TOOLSET_VERIFIED) echo fake ;;
            PACKAGES) echo \$out/packages ;;
            PKG_INFO) echo "\$out/pkg_info -K \$out/native-db" ;;
            NATIVE_PKG_ADD_CMD) echo \$out/pkg_info ;;
            *) value "\$varname" ;;
        esac ;;
    show-vars) for n in \$varnames; do value \$n; done ;;
    clean) ;;
    # build makes the package of a node to replace first (see exclusive).
    package) ;;
    install|replace)
        name=\$(value PKGNAME)
        if [ \$target = install ] && ls \$out/native-db/\$(value PKGBASE)-[0-9]* > /dev/null 2>&1; then
            echo "\$name: an older version is already installed"; exit 1
        fi
        rm -f \$out/native-db/\$(value PKGBASE)-[0-9]*
        : > \$out/native-db/\$name ;;
    package-install)
        mkdir -p \$out/packages/All; echo \$pkg > \$out/packages/All/\$(value PKGNAME).tgz ;;
    *) echo "bmake: don't know how to make \$target. Stop"; exit 2 ;;
esac
WRAP
chmod +x "$out/bmake" "$out/pkg_info"
fail() { echo "FAIL: $*" >&2; exit 1; }
bulk() {
    BMAKE=$out/bmake MAKECONF=$out/mk.conf PKGSRCDIR=$out/tree CROSS_BULK_CPUS=1 CROSS_BULK_JOBS=1 \
        CROSS_BULK_VARS_CACHE=no sh "$ports/scripts/cross-bulk.sh" "$@"
}
echo t/a > "$out/list"
bulk order "$out/list" "$out/state" > "$out/order.log" 2>&1 || fail "order: $(cat "$out/order.log")"
grep -qx 'd/tclsh@native s/sqlite3@native' "$out/state/edges" ||
    fail 'order kept s/sqlite3@native a leaf although the native prefix has the older sqlite3-3.54.1'
! grep -q 'e/cmake@native' "$out/state/edges" ||
    fail 'order walked the tools of a native node whose installed package is current or newer'
: > "$out/calls"
bulk build "$out/state/order" "$out/state" > "$out/build.log" 2>&1 || fail "build: $(cat "$out/build.log")"
[ -e "$out/native-db/sqlite3-3.54.1nb1" ] && [ ! -e "$out/native-db/sqlite3-3.54.1" ] ||
    fail "the older native sqlite3 counted as done: $(ls "$out/native-db")"
grep -q '/s/sqlite3 .* replace' "$out/calls" || fail 'sqlite3 was not replaced with pkgsrc replace'
[ -e "$out/native-db/clang-23.1.4nb11" ] || fail 'the newer native clang was replaced'
! grep -Eq '/(c/clang|m/m4) .* (install|replace)' "$out/calls" || fail 'a current native node was built'
grep -q '^s/sqlite3@native ' "$out/state/done" || fail "s/sqlite3@native not done: $(cat "$out/state/done")"
echo 'PASS: an older native package is rebuilt; a current or newer one stays done'

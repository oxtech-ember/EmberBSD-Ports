#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). scripts/cross-bulk.sh does not build a
# native tool again when the native prefix already has it at its version,
# but its consumers still run it, and it runs its runtime dependencies. The
# native prefix of the test has meson-1.0 (current) and ninja-1.0; the tree
# has ninja-1.0nb1. Target t/app needs meson, and meson needs ninja at run
# time. Order must build ninja before meson's consumer t/app starts, and must
# not follow the build tools of the installed meson (py, not installed).
# Usage: cross-bulk-native-runtime-order.sh NEW_OUTPUT
set -eu
[ "$#" = 1 ] || { echo 'Usage: cross-bulk-native-runtime-order.sh NEW_OUTPUT' >&2; exit 2; }
out=$1
case "$out" in /*) ;; *) echo 'NEW_OUTPUT must be absolute' >&2; exit 2 ;; esac
case "$out" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2 ;; esac
[ ! -e "$out" ] || exit 2
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
for p in t/app d/meson d/ninja l/py; do mkdir -p "$out/tree/$p"; done
mkdir -p "$out/packages/All" "$out/work" "$out/native-db" "$out/vars"
: > "$out/native-db/meson-1.0"
: > "$out/native-db/ninja-1.0"
# vars/PKG.MODE.VARNAME holds a value; a missing file is empty.
v() { printf '%s\n' "$4" > "$out/vars/$1.$2.$3"; }
v app target PKGNAME app-1.0
v app target TOOL_DEPENDS 'meson>=1.0:../../d/meson'
v meson native PKGNAME meson-1.0
v meson native DEPENDS 'ninja>=1.0:../../d/ninja'
v meson native TOOL_DEPENDS 'py>=1:../../l/py'
v ninja native PKGNAME ninja-1.0nb1
v py native PKGNAME py-1.0
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
    *) echo "bmake: don't know how to make \$target. Stop"; exit 2 ;;
esac
WRAP
chmod +x "$out/bmake" "$out/pkg_info"
fail() { echo "FAIL: $*" >&2; exit 1; }
bulk() {
    BMAKE=$ports/scripts/tests/cross-bulk-bmake-proxy.sh CROSS_BULK_TEST_REAL_BMAKE=$out/bmake \
        MAKECONF=$out/mk.conf PKGSRCDIR=$out/tree CROSS_BULK_CPUS=1 CROSS_BULK_JOBS=1 \
        CROSS_BULK_VARS_CACHE=no sh "$ports/scripts/cross-bulk.sh" "$@"
}
echo t/app > "$out/list"
bulk order "$out/list" "$out/state" > "$out/order.log" 2>&1 || fail "order: $(cat "$out/order.log")"
e=$out/state/edges
grep -qx 'd/meson@native t/app' "$e" || fail "no meson -> app edge: $(cat "$e")"
grep -qx 'd/ninja@native d/meson@native' "$e" || fail "the installed meson lost its runtime ninja: $(cat "$e")"
! grep -q '^l/py@native' "$e" "$out/state/order" || fail "order follows the build tools of the installed meson: $(cat "$e")"
n=$(grep -n '^d/ninja@native$' "$out/state/order" | cut -d: -f1)
m=$(grep -n '^d/meson@native$' "$out/state/order" | cut -d: -f1)
a=$(grep -n '^t/app$' "$out/state/order" | cut -d: -f1)
[ -n "$n" ] && [ -n "$m" ] && [ -n "$a" ] && [ "$n" -lt "$m" ] && [ "$m" -lt "$a" ] ||
    fail "order: $(cat "$out/state/order")"
echo 'PASS: an installed native tool keeps its runtime dependencies ahead of its consumers'

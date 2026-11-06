#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# Order resolves a dependency directory from the package that declares it.
# A same-category sibling (../mesa-generators) and a dotted relative path
# (./../helper) are category/package nodes, just as ../../category/package is.
# An entry that leaves the tree is refused rather than omitted.
# Target tools are queried in the cross-fed native context. Tools of those
# tools keep the plain native context. An installed native package is current
# only at the tree PKGNAME or newer, so an older exact dependency is built
# and its own tools stay in the graph.
# Usage: cross-bulk-relative-depends.sh NEW_OUTPUT
set -eu
[ "$#" = 1 ] || { echo 'Usage: cross-bulk-relative-depends.sh NEW_OUTPUT' >&2; exit 2; }
out=$1
case "$out" in /*) ;; *) echo 'NEW_OUTPUT must be absolute' >&2; exit 2 ;; esac
case "$out" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2 ;; esac
[ ! -e "$out" ] || exit 2
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
python=${TEST_PYTHON:-$(command -v python3)}
[ -n "$python" ] || { echo 'python3 is required' >&2; exit 2; }
mkdir -p "$out/tree/pkgtools/pkg_install" "$out/tree/graphics/MesaLib" \
    "$out/tree/graphics/mesa-generators" "$out/tree/graphics/widget" \
    "$out/tree/graphics/helper" "$out/tree/graphics/bad" \
    "$out/tree/devel/flex" "$out/tree/devel/bison" \
    "$out/tree/x11/libX11" \
    "$out/native-db" "$out/sdk/scripts" "$out/packages/All"
: > "$out/mk.conf"
printf 'print(1)\n' > "$out/sdk/scripts/resolve-jobs.py"
cat > "$out/pkg_info" <<'WRAP'
#!/bin/sh
db=$2
pattern=$4
[ "$1" = -K ] && [ "$3" = -e ] || exit 2
case "$pattern" in
    *'>='*)
        base=${pattern%%>=*}
        want=${pattern#*>=}
        found=1
        for installed in "$db/$base"-[0-9]*; do
            [ -e "$installed" ] || continue
            have=${installed##*/}
            have=${have#"$base"-}
            if [ "$(printf '%s\n%s\n' "$want" "$have" | sort -V | tail -n 1)" = "$have" ]; then
                exit 0
            fi
            found=0
        done
        exit 1 ;;
esac
[ -e "$db/$pattern" ] && exit 0
for installed in "$db/$pattern"-[0-9]*; do
    [ -e "$installed" ] && exit 0
done
exit 1
WRAP
cat > "$out/bmake" <<WRAP
#!/bin/sh
out=$out
printf '%s\n' "\$*" >> "\$out/calls"
dir= target= varname= varnames= role=target
while [ "\$#" -gt 0 ]; do
    case "\$1" in
        -C) dir=\$2; shift 2 ;;
        VARNAME=*) varname=\${1#VARNAME=}; shift ;;
        VARNAMES=*) varnames=\${1#VARNAMES=}; shift ;;
        USE_CROSS_COMPILE=no) role=native; shift ;;
        *=*) shift ;;
        *) target=\$1; shift ;;
    esac
done
pkg=\${dir##*/}
value() {
    case "\$pkg:\$role:\$1" in
        MesaLib:target:TOOL_DEPENDS)
            echo 'mesa-generators-26.2.6nb20:../mesa-generators flex>=2.6.4:../../devel/flex' ;;
        MesaLib:target:BUILD_DEPENDS)
            echo '{libX11>=1.8:alt,libX11>=1.8}:../../x11/libX11' ;;
        mesa-generators:native:TOOL_DEPENDS) echo 'bison>=3.8.2:../../devel/bison' ;;
        widget:target:TOOL_DEPENDS) echo 'helper-1.0:./../helper' ;;
        bad:target:TOOL_DEPENDS) echo 'evil>=1:../../../../tmp/evil' ;;
        mesa-generators:*:PKGNAME) echo mesa-generators-26.2.6nb20 ;;
        mesa-generators:*:PKGBASE) echo mesa-generators ;;
        MesaLib:*:PKGNAME) echo MesaLib-26.2.6nb20 ;;
        MesaLib:*:PKGBASE) echo MesaLib ;;
        flex:*:PKGNAME) echo flex-2.6.4 ;;
        bison:*:PKGNAME) echo bison-3.8.2 ;;
        helper:*:PKGNAME) echo helper-1.0 ;;
        *:*:PKGNAME) echo "\$pkg-1.0" ;;
        *:*:PKGBASE) echo "\$pkg" ;;
        *) echo ;;
    esac
}
case "\$target" in
    show-var)
        case "\$varname" in
            EMBERBSD_NATIVE_TOOLSET_VERIFIED) echo fake ;;
            PKG_INFO) echo "\$out/pkg_info -K \$out/native-db" ;;
            CROSSTARGETSETTINGS) echo 'TARGET_OPSYS=NetBSD TARGET_MACHINE_ARCH=aarch64' ;;
            *) value "\$varname" ;;
        esac ;;
    show-vars) for name in \$varnames; do value "\$name"; done ;;
    *) echo "unexpected bmake target: \$target" >&2; exit 2 ;;
esac
WRAP
chmod +x "$out/bmake" "$out/pkg_info"
fail() { echo "FAIL: $*" >&2; exit 1; }
before() {
    later=$(awk -v first="$1" -v second="$2" '
        $0 == first { seen = 1 }
        $0 == second { if (!seen) bad = 1 }
        END { exit bad }' "$3") || fail "$1 is not ordered before $2"
}
bulk() {
    BMAKE=$ports/scripts/tests/cross-bulk-bmake-proxy.sh CROSS_BULK_TEST_REAL_BMAKE=$out/bmake \
        MAKECONF=$out/mk.conf PKGSRCDIR=$out/tree CROSS_BULK_JOBS=1 \
        CROSS_BULK_VARS_CACHE=no CROSS_BULK_TEST_HOST_PYTHON="$python" \
        CROSS_BULK_TEST_SDK_SOURCE="$out/sdk" \
        sh "$ports/scripts/cross-bulk.sh" "$@"
}
order_case() {
    label=$1
    : > "$out/calls"
    rm -rf "$out/state-$label"
    printf '%s\n' graphics/MesaLib graphics/widget > "$out/list"
    bulk order "$out/list" "$out/state-$label" > "$out/order-$label.log" 2>&1 ||
        fail "$label order: $(cat "$out/order-$label.log")"
    state=$out/state-$label
    grep -qx 'graphics/mesa-generators@native graphics/MesaLib' "$state/edges" ||
        fail "$label did not keep the sibling generator edge"
    grep -qx 'devel/flex@native graphics/MesaLib' "$state/edges" ||
        fail "$label did not keep the canonical flex edge"
    grep -qx 'x11/libX11 graphics/MesaLib' "$state/edges" ||
        fail "$label did not keep the directory after the last colon"
    grep -qx 'graphics/helper@native graphics/widget' "$state/edges" ||
        fail "$label did not resolve ./../helper"
    grep -qx 'graphics/mesa-generators@native mesa-generators-26.2.6nb20' "$state/packages" ||
        fail "$label did not record the exact generator package"
    before graphics/mesa-generators@native graphics/MesaLib "$state/order"
    before devel/flex@native graphics/MesaLib "$state/order"
    before x11/libX11 graphics/MesaLib "$state/order"
    before graphics/helper@native graphics/widget "$state/order"
    generator=$(grep -- "-C $out/tree/graphics/mesa-generators " "$out/calls" | grep show-vars || true)
    bison=$(grep -- "-C $out/tree/devel/bison " "$out/calls" | grep show-vars || true)
    mesa=$(grep -- "-C $out/tree/graphics/MesaLib " "$out/calls" | grep show-vars || true)
    [ -n "$generator" ] || fail "$label did not query the generator package"
    case "$generator" in
        *'USE_CROSS_COMPILE=no'*'TARGET_MACHINE_ARCH=aarch64'*) ;;
        *) fail "$label generator query lost the cross-fed native context: $generator" ;;
    esac
    case "$mesa" in
        *USE_CROSS_COMPILE=no*) fail "$label queried MesaLib as a native package" ;;
    esac
    if [ "$2" = tools ]; then
        grep -qx 'devel/bison@native graphics/mesa-generators@native' "$state/edges" ||
            fail "$label treated the older or absent generator as current"
        before devel/bison@native graphics/mesa-generators@native "$state/order"
        [ -n "$bison" ] || fail "$label did not query bison"
        case "$bison" in
            *USE_CROSS_COMPILE=no*) ;;
            *) fail "$label bison query was not native: $bison" ;;
        esac
        case "$bison" in
            *TARGET_MACHINE_ARCH=*) fail "$label gave bison the target settings: $bison" ;;
        esac
    else
        ! grep -q 'devel/bison@native' "$state/edges" ||
            fail "$label walked tools of the already compatible generator"
        [ -z "$bison" ] || fail "$label queried bison although the generator is current"
    fi
}
order_case absent tools
: > "$out/native-db/mesa-generators-26.2.6nb19"
order_case nb19 tools
rm -f "$out/native-db/mesa-generators-26.2.6nb19"
: > "$out/native-db/mesa-generators-26.2.6nb20"
order_case exact leaf
: > "$out/calls"
rm -rf "$out/state-escape"
printf '%s\n' graphics/bad > "$out/escape-list"
if bulk order "$out/escape-list" "$out/state-escape" > "$out/escape.log" 2>&1; then
    fail 'a dependency path outside the tree was accepted'
fi
grep -q 'dependency path leaves the pkgsrc tree: ../../../../tmp/evil from graphics/bad' "$out/escape.log" ||
    fail "escape was not reported: $(cat "$out/escape.log")"
echo 'PASS: relative dependency paths, exact generator compatibility, and cross-fed native context'

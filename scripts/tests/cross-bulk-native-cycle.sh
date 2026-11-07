#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# scripts/cross-bulk.sh may break a dependency cycle between two native
# nodes to build only with an edge whose pattern the native prefix already
# satisfies. The native prefix of the test has coreutils-9.12 and
# perl-5.44.0nb11; the tree has coreutils-9.12nb1, which needs perl>=5.0,
# and perl-5.44.0nb14, which needs coreutils>=5.2.1. Neither is current, so
# both are built, and each needs the other. pkgsrc builds either one with
# the installed other, so order must drop one of the two satisfied edges
# and keep the other. A cycle in which an edge is not satisfied by the
# native prefix (x needs y>=1, y needs x>=1, nothing installed) is still
# refused.
# Usage: cross-bulk-native-cycle.sh NEW_OUTPUT
set -eu
[ "$#" = 1 ] || { echo 'Usage: cross-bulk-native-cycle.sh NEW_OUTPUT' >&2; exit 2; }
out=$1
case "$out" in /*) ;; *) echo 'NEW_OUTPUT must be absolute' >&2; exit 2 ;; esac
case "$out" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2 ;; esac
[ ! -e "$out" ] || exit 2
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
for p in t/a t/b t/c s/coreutils l/perl5 x/x y/y n/a n/b n/c; do mkdir -p "$out/tree/$p"; done
mkdir -p "$out/packages/All" "$out/work" "$out/native-db" "$out/vars"
: > "$out/native-db/coreutils-9.12"
: > "$out/native-db/perl-5.44.0nb11"
# vars/PKG.MODE.VARNAME holds a value; a missing file is empty.
v() { printf '%s\n' "$4" > "$out/vars/$1.$2.$3"; }
v a target PKGNAME a-1.0
v a target TOOL_DEPENDS 'coreutils>=5:../../s/coreutils perl>=5.0:../../l/perl5'
v coreutils native PKGNAME coreutils-9.12nb1
v coreutils native TOOL_DEPENDS 'perl>=5.0:../../l/perl5'
v perl5 native PKGNAME perl-5.44.0nb14
v perl5 native TOOL_DEPENDS 'coreutils>=5.2.1:../../s/coreutils'
v b target PKGNAME b-1.0
v b target TOOL_DEPENDS 'x>=1:../../x/x'
v x native PKGNAME x-1.0
v x native TOOL_DEPENDS 'y>=1:../../y/y'
v y native PKGNAME y-1.0
v y native TOOL_DEPENDS 'x>=1:../../x/x'
# Two cycles share a soft edge. After dropping a->b, the remaining
# a->c->b->a cycle still reports a and b, but a->b is no longer active.
# The sorter must choose the remaining active soft edge a->c.
: > "$out/native-db/a-1.0"
: > "$out/native-db/b-1.0"
: > "$out/native-db/c-1.0"
v c target PKGNAME c-1.0
v c target TOOL_DEPENDS 'a>=1:../../n/a'
v a native PKGNAME a-2.0
v a native TOOL_DEPENDS 'b>=1:../../n/b'
v b native PKGNAME b-2.0
v b native TOOL_DEPENDS 'a>=1:../../n/a c>=1:../../n/c'
v c native PKGNAME c-2.0
v c native TOOL_DEPENDS 'a>=1:../../n/a'
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
    BMAKE=$ports/scripts/tests/cross-bulk-bmake-proxy.sh CROSS_BULK_TEST_REAL_BMAKE=$out/bmake \
        MAKECONF=$out/mk.conf PKGSRCDIR=$out/tree CROSS_BULK_CPUS=1 CROSS_BULK_JOBS=1 \
        CROSS_BULK_VARS_CACHE=no sh "$ports/scripts/cross-bulk.sh" "$@"
}
echo t/a > "$out/list"
bulk order "$out/list" "$out/state" > "$out/order.log" 2>&1 || fail "order: $(cat "$out/order.log")"
e=$out/state/edges
grep -qx 's/coreutils@native l/perl5@native' "$e" || fail "the edge coreutils -> perl was dropped: $(cat "$e")"
! grep -qx 'l/perl5@native s/coreutils@native' "$e" || fail "the satisfied cycle edge perl -> coreutils was kept: $(cat "$e")"
c=$(grep -n '^s/coreutils@native$' "$out/state/order" | cut -d: -f1)
p=$(grep -n '^l/perl5@native$' "$out/state/order" | cut -d: -f1)
[ -n "$c" ] && [ -n "$p" ] && [ "$c" -lt "$p" ] || fail "order: $(cat "$out/state/order")"
grep -qx 'Cycle broken: s/coreutils@native builds with the installed l/perl5@native (pattern satisfied)' "$out/order.log" || fail "the dropped edge is not reported: $(cat "$out/order.log")"
echo t/b > "$out/list-b"
! bulk order "$out/list-b" "$out/state-b" > "$out/order-b.log" 2>&1 || fail 'order accepted a cycle of unsatisfied edges'
grep -q 'Refused: the dependency graph has a cycle' "$out/order-b.log" || fail "order-b: $(cat "$out/order-b.log")"
# Keep the production order command bounded: the regression is an infinite
# retry with no graph change, not a slow package query.
echo t/c > "$out/list-c"
if python3 - "$ports" "$out" <<'PY'
import os
import subprocess
import sys

ports, out = sys.argv[1:]
env = os.environ.copy()
env.update({
    "BMAKE": ports + "/scripts/tests/cross-bulk-bmake-proxy.sh",
    "CROSS_BULK_TEST_REAL_BMAKE": out + "/bmake",
    "MAKECONF": out + "/mk.conf",
    "PKGSRCDIR": out + "/tree",
    "CROSS_BULK_CPUS": "1",
    "CROSS_BULK_JOBS": "1",
    "CROSS_BULK_VARS_CACHE": "no",
})
try:
    result = subprocess.run(
        ["sh", ports + "/scripts/cross-bulk.sh", "order",
         out + "/list-c", out + "/state-c"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        timeout=5, env=env, check=False)
except subprocess.TimeoutExpired as exc:
    output = exc.stdout or ""
    if isinstance(output, bytes):
        output = output.decode(errors="replace")
    open(out + "/order-c.log", "w").write(output)
    print("bounded production order timed out", file=sys.stderr)
    raise SystemExit(124)
open(out + "/order-c.log", "w").write(result.stdout)
raise SystemExit(result.returncode)
PY
then
    :
else
    fail "overlapping native cycles did not order: $(tail -n 12 "$out/order-c.log")"
fi
grep -qx 'n/b@native n/a@native' "$out/state-c/edges" || fail "the first cycle cut was not retained: $(cat "$out/state-c/edges")"
! grep -qx 'n/a@native n/b@native' "$out/state-c/edges" || fail "the first soft edge remains active: $(cat "$out/state-c/edges")"
! grep -qx 'n/a@native n/c@native' "$out/state-c/edges" || fail "the remaining active cycle edge was not cut: $(cat "$out/state-c/edges")"
grep -qx 'n/c@native n/b@native' "$out/state-c/edges" || fail "the uncut edge in the residual cycle is missing: $(cat "$out/state-c/edges")"
echo 'PASS: a native cycle breaks at a satisfied edge; an unsatisfied cycle is refused'

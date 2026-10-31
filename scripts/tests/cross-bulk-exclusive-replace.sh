#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). pkgsrc replace (pkg_add -U) deletes the
# files of the installed package before it adds the new ones. When
# scripts/cross-bulk.sh replaced libffi in the native prefix while a target
# build ran, that build's compiler wrapper, a tool linked with the native
# libffi, failed with "Library not loaded: .../lib/libffi.8.dylib". build
# must run a replace, native or target, only when no other job runs, and
# start no job meanwhile. The test runs four jobs at once: two target
# builds, an older native libffi to replace and an older target perl in the
# sysroot to replace; a build or a replace that sees another replace at
# work records an overlap.
# Usage: cross-bulk-exclusive-replace.sh NEW_OUTPUT
set -eu
[ "$#" = 1 ] || { echo 'Usage: cross-bulk-exclusive-replace.sh NEW_OUTPUT' >&2; exit 2; }
out=$1
case "$out" in /*) ;; *) echo 'NEW_OUTPUT must be absolute' >&2; exit 2 ;; esac
case "$out" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2 ;; esac
[ ! -e "$out" ] || exit 2
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
for p in t/a t/b t/x l/libffi l/perl; do mkdir -p "$out/tree/$p"; done
mkdir -p "$out/packages/All" "$out/work" "$out/native-db" "$out/target-db" "$out/vars" "$out/active"
: > "$out/native-db/libffi-3.5"
: > "$out/target-db/perl-5.44.0nb9"
: > "$out/overlaps"
# vars/PKG.MODE.VARNAME holds a value; a missing file is empty.
v() { printf '%s\n' "$4" > "$out/vars/$1.$2.$3"; }
v a target PKGNAME a-1.0
v b target PKGNAME b-1.0
v x target PKGNAME x-1.0
v x target TOOL_DEPENDS 'libffi>=3.5nb1:../../l/libffi'
v libffi native PKGNAME libffi-3.5nb1
v perl target PKGNAME perl-5.44.0nb10
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
# A build or a replace takes three seconds; it looks for the work of others
# ten times meanwhile.
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
db=\$out/target-db
[ \$mode = target ] || db=\$out/native-db
# work KIND: be at work for three seconds and record another job's replace.
work() {
    : > \$out/active/\$pkg.\$1
    i=0
    while [ \$i -lt 10 ]; do
        for f in \$out/active/*; do
            [ "\$f" != \$out/active/\$pkg.\$1 ] || continue
            case "\$1 \$f" in
                replace\ *|*.replace) echo "\$pkg \$1 with \${f##*/}" >> \$out/overlaps ;;
            esac
        done
        sleep 0.3
        i=\$((i + 1))
    done
    rm -f \$out/active/\$pkg.\$1
}
case "\$target" in
    show-var)
        case "\$varname" in
            EMBERBSD_NATIVE_TOOLSET_VERIFIED) echo fake ;;
            PACKAGES) echo \$out/packages ;;
            PKG_INFO) echo "\$out/pkg_info -K \$db" ;;
            NATIVE_PKG_ADD_CMD) echo \$out/pkg_info ;;
            *) value "\$varname" ;;
        esac ;;
    show-vars) for n in \$varnames; do value \$n; done ;;
    clean) ;;
    package)
        echo \$pkg > \$out/packages/All/\$(value PKGNAME).tgz ;;
    package-install|install)
        name=\$(value PKGNAME)
        for f in \$db/\$(value PKGBASE)-[0-9]*; do
            [ -e "\$f" ] || continue
            echo "pkg_add: A different version of \$name is already installed: \${f##*/}"; exit 1
        done
        work build
        echo \$pkg > \$out/packages/All/\$name.tgz
        : > \$db/\$name ;;
    replace)
        name=\$(value PKGNAME)
        # pkgsrc replace makes the package first when it is not there.
        echo \$pkg > \$out/packages/All/\$name.tgz
        rm -f \$db/\$(value PKGBASE)-[0-9]*
        work replace
        : > \$db/\$name ;;
    *) echo "bmake: don't know how to make \$target. Stop"; exit 2 ;;
esac
WRAP
chmod +x "$out/bmake" "$out/pkg_info"
fail() { echo "FAIL: $*" >&2; exit 1; }
bulk() {
    BMAKE=$out/bmake MAKECONF=$out/mk.conf PKGSRCDIR=$out/tree CROSS_BULK_CPUS=4 CROSS_BULK_JOBS=4 \
        CROSS_BULK_VARS_CACHE=no sh "$ports/scripts/cross-bulk.sh" "$@"
}
printf '%s\n' t/a t/b l/perl t/x > "$out/list"
bulk order "$out/list" "$out/state" > "$out/order.log" 2>&1 || fail "order: $(cat "$out/order.log")"
grep -qx 'l/libffi@native t/x' "$out/state/edges" || fail "t/x does not wait for l/libffi@native: $(cat "$out/state/edges")"
: > "$out/calls"
bulk build "$out/state/order" "$out/state" > "$out/build.log" 2>&1 || fail "build: $(cat "$out/build.log")"
[ ! -s "$out/state/failed" ] || fail "failed: $(cat "$out/state/failed")"
grep -q '/l/libffi .* replace' "$out/calls" || fail 'the older native libffi was not replaced'
grep -q '/l/perl replace' "$out/calls" || fail 'the older target perl was not replaced'
[ -e "$out/native-db/libffi-3.5nb1" ] && [ -e "$out/target-db/perl-5.44.0nb10" ] ||
    fail "not replaced: $(ls "$out/native-db" "$out/target-db")"
for p in t/a t/b l/perl t/x l/libffi@native; do
    grep -q "^$p " "$out/state/done" || fail "$p not done: $(cat "$out/state/done")"
done
[ ! -s "$out/overlaps" ] || fail "a replace ran with other jobs: $(sort -u "$out/overlaps" | tr '\n' ';')"
echo 'PASS: a native or target replace runs alone; the other jobs finish first'

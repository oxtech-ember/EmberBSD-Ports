#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). scripts/cross-bulk.sh installs a target
# package into a sysroot that may already have another version of it, for
# example ada-idna-0.7.0 from an earlier pass when the tree now builds
# ada-idna-0.7.0nb1. pkg_add refuses to install over it ("A different
# version of ... is already installed"), so build must make the package
# and then replace the installed one (pkgsrc replace, pkg_add -U). A
# package that the sysroot does not have yet still uses package-install.
# Usage: cross-bulk-target-replace.sh NEW_OUTPUT
set -eu
[ "$#" = 1 ] || { echo 'Usage: cross-bulk-target-replace.sh NEW_OUTPUT' >&2; exit 2; }
out=$1
case "$out" in /*) ;; *) echo 'NEW_OUTPUT must be absolute' >&2; exit 2 ;; esac
case "$out" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2 ;; esac
[ ! -e "$out" ] || exit 2
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
for p in d/ada-idna d/ada-url; do mkdir -p "$out/tree/$p"; done
mkdir -p "$out/packages/All" "$out/work" "$out/native-db" "$out/target-db" "$out/vars"
: > "$out/target-db/ada-idna-0.7.0"
# vars/PKG.MODE.VARNAME holds a value; a missing file is empty.
v() { printf '%s\n' "$4" > "$out/vars/$1.$2.$3"; }
v ada-idna target PKGNAME ada-idna-0.7.0nb1
v ada-url target PKGNAME ada-url-3.0.0
v ada-url target DEPENDS 'ada-idna>=0.7.0nb1:../../d/ada-idna'
# pkg_info -K DB -e PATTERN for a BASE pattern.
cat > "$out/pkg_info" <<'WRAP'
#!/bin/sh
for f in "$2/$4"-[0-9]*; do [ -e "$f" ] && exit 0; done
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
db=\$out/target-db
[ \$mode = target ] || db=\$out/native-db
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
    package) echo \$pkg > \$out/packages/All/\$(value PKGNAME).tgz ;;
    package-install)
        name=\$(value PKGNAME)
        for f in \$db/\$(value PKGBASE)-[0-9]*; do
            [ -e "\$f" ] || continue
            echo "pkg_add: A different version of \$name is already installed: \${f##*/}"; exit 1
        done
        echo \$pkg > \$out/packages/All/\$name.tgz
        : > \$db/\$name ;;
    replace)
        name=\$(value PKGNAME)
        [ -f \$out/packages/All/\$name.tgz ] || { echo "replace: no package \$name"; exit 1; }
        rm -f \$db/\$(value PKGBASE)-[0-9]*
        : > \$db/\$name ;;
    *) echo "bmake: don't know how to make \$target. Stop"; exit 2 ;;
esac
WRAP
chmod +x "$out/bmake" "$out/pkg_info"
fail() { echo "FAIL: $*" >&2; exit 1; }
bulk() {
    BMAKE=$out/bmake MAKECONF=$out/mk.conf PKGSRCDIR=$out/tree CROSS_BULK_CPUS=1 CROSS_BULK_JOBS=1 \
        CROSS_BULK_VARS_CACHE=no sh "$ports/scripts/cross-bulk.sh" "$@"
}
echo d/ada-url > "$out/list"
bulk order "$out/list" "$out/state" > "$out/order.log" 2>&1 || fail "order: $(cat "$out/order.log")"
: > "$out/calls"
bulk build "$out/state/order" "$out/state" > "$out/build.log" 2>&1 || fail "build: $(cat "$out/build.log")"
[ ! -s "$out/state/failed" ] || fail "failed: $(cat "$out/state/failed") $(cat "$out/state/logs/d_ada-idna.log" 2> /dev/null)"
[ -e "$out/target-db/ada-idna-0.7.0nb1" ] && [ ! -e "$out/target-db/ada-idna-0.7.0" ] ||
    fail "the older ada-idna in the sysroot was not replaced: $(ls "$out/target-db")"
grep -q '/d/ada-idna replace' "$out/calls" || fail 'ada-idna was not installed with pkgsrc replace'
grep -q '/d/ada-url package-install' "$out/calls" || fail 'a new package did not use package-install'
grep -q '^d/ada-idna ada-idna-0.7.0nb1 ' "$out/state/done" || fail "d/ada-idna not done: $(cat "$out/state/done")"
grep -q '^d/ada-url ada-url-3.0.0 ' "$out/state/done" || fail "d/ada-url not done: $(cat "$out/state/done")"
echo 'PASS: a target package replaces another version in the sysroot; a new one is installed'

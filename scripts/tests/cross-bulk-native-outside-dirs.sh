#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). A native package built before the native
# profile kept rc.d in the host prefix recorded "# DIR: /etc/rc.d" in its
# +DIRS. pkg_add -U then ran its +DIRS REMOVE, whose "rmdir -p /etc/rc.d"
# waited on a macOS privacy prompt with the database lock held. The
# STATE/run/pkg_add wrapper of scripts/cross-bulk.sh build must mark every
# refcounted path outside the recording package's prefix as preexisting
# before it installs into the native database, so REMOVE leaves it alone.
# Paths inside the prefix and target databases stay unchanged. The fake
# pkg_add below applies the +DIRS and +FILES REMOVE rule of pkgsrc
# mk/pkginstall and records the paths that it would remove.
# Usage: cross-bulk-native-outside-dirs.sh NEW_OUTPUT
set -eu
[ "$#" = 1 ] || { echo 'Usage: cross-bulk-native-outside-dirs.sh NEW_OUTPUT' >&2; exit 2; }
out=$1
case "$out" in /*) ;; *) echo 'NEW_OUTPUT must be absolute' >&2; exit 2 ;; esac
case "$out" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2 ;; esac
[ ! -e "$out" ] || exit 2
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
for p in t/a n/dbus; do mkdir -p "$out/tree/$p"; done
mkdir -p "$out/packages/All" "$out/work" "$out/vars" "$out/prefix" "$out/target-db"
db=$out/native-db
old=$db/dbus-1.0nb1
mkdir -p "$old"
printf '@cwd %s\n@name dbus-1.0nb1\n' "$out/prefix" > "$old/+CONTENTS"
printf '# DIR: %s m\n# DIR: %s m\n# DIR: share/dbus m\n' \
    "$out/outside/rc.d" "$out/prefix/var/run/dbus" > "$old/+DIRS"
printf '# FILE: %s cr share/examples/rc.d/dbus 0755\n' "$out/outside/rc.d/dbus" > "$old/+FILES"
# The refcount shadows as pkgsrc leaves them: a token, no +PREEXISTING.
for s in dirs$out/outside/rc.d dirs$out/prefix/var/run/dbus files$out/outside/rc.d/dbus; do
    mkdir -p "$db.refcount/$s"; echo "$old" > "$db.refcount/$s/dbus-1.0nb1"
done
# A target database with the same pattern is not the native prefix.
mkdir -p "$out/target-db/x-1.0" "$out/target-db.refcount/dirs$out/outside/x"
printf '@cwd /usr/pkg\n' > "$out/target-db/x-1.0/+CONTENTS"
printf '# DIR: %s m\n' "$out/outside/x" > "$out/target-db/x-1.0/+DIRS"
echo x > "$out/target-db.refcount/dirs$out/outside/x/x-1.0"
v() { printf '%s\n' "$4" > "$out/vars/$1.$2.$3"; }
v a target PKGNAME a-1.0
v a target TOOL_DEPENDS 'dbus>=1.0nb2:../../n/dbus'
v dbus native PKGNAME dbus-1.0nb2
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
# The real pkg_add: -K DB -U NAME replaces the installed package of NAME's
# base; the old package's REMOVE skips a path whose shadow is preexisting.
cat > "$out/real_pkg_add" <<WRAP
#!/bin/sh
out=$out
WRAP
cat >> "$out/real_pkg_add" <<'WRAP'
db=$2 name=$4
for old in "$db/${name%-*}"-[0-9]*; do
    [ -d "$old" ] || continue
    for s in $(cd "$db.refcount" && find dirs files -name "${old##*/}"); do
        shadow=$db.refcount/${s%/*}
        [ -f "$shadow/+PREEXISTING" ] || echo "/${shadow#"$db.refcount/"*/}" >> "$out/removed"
        rm -rf "$shadow"
    done
    rm -rf "$old"
done
mkdir -p "$db/$name"
WRAP
cat > "$out/bmake" <<WRAP
#!/bin/sh
out=$out
dir= target= varname= varnames= mode=target pkgadd=
while [ "\$#" -gt 0 ]; do
    case "\$1" in
        -C) dir=\$2; shift 2 ;;
        VARNAME=*) varname=\${1#VARNAME=}; shift ;;
        VARNAMES=*) varnames=\${1#VARNAMES=}; shift ;;
        NATIVE_PKG_ADD_CMD=*) pkgadd=\${1#NATIVE_PKG_ADD_CMD=}; shift ;;
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
            NATIVE_PKG_ADD_CMD) echo \$out/real_pkg_add ;;
            *) value "\$varname" ;;
        esac ;;
    show-vars) for n in \$varnames; do value \$n; done ;;
    clean|package) ;;
    install|replace)
        [ -n "\$pkgadd" ] || { echo 'NATIVE_PKG_ADD_CMD was not passed'; exit 1; }
        "\$pkgadd" -K "\$out/target-db" -U x-1.0
        "\$pkgadd" -K "\$out/native-db" -U \$(value PKGNAME) ;;
    package-install)
        mkdir -p \$out/packages/All; echo \$pkg > \$out/packages/All/\$(value PKGNAME).tgz ;;
    *) echo "bmake: don't know how to make \$target. Stop"; exit 2 ;;
esac
WRAP
chmod +x "$out/bmake" "$out/pkg_info" "$out/real_pkg_add"
fail() { echo "FAIL: $*" >&2; exit 1; }
bulk() {
    BMAKE=$ports/scripts/tests/cross-bulk-bmake-proxy.sh CROSS_BULK_TEST_REAL_BMAKE=$out/bmake \
        MAKECONF=$out/mk.conf PKGSRCDIR=$out/tree CROSS_BULK_CPUS=1 CROSS_BULK_JOBS=1 \
        CROSS_BULK_VARS_CACHE=no sh "$ports/scripts/cross-bulk.sh" "$@"
}
echo t/a > "$out/list"
: > "$out/removed"
bulk order "$out/list" "$out/state" > "$out/order.log" 2>&1 || fail "order: $(cat "$out/order.log")"
bulk build "$out/state/order" "$out/state" > "$out/build.log" 2>&1 || fail "build: $(cat "$out/build.log")"
[ -d "$db/dbus-1.0nb2" ] && [ ! -e "$old" ] || fail "dbus was not replaced: $(cat "$out/build.log")"
! grep -q "^$out/outside/rc.d" "$out/removed" ||
    fail "the native replace removed paths outside the native prefix: $(cat "$out/removed")"
grep -qx "$out/prefix/var/run/dbus" "$out/removed" ||
    fail "a path inside the native prefix was kept: $(cat "$out/removed")"
grep -qx "$out/outside/x" "$out/removed" ||
    fail "a target database was changed: $(cat "$out/removed")"
echo 'PASS: a native replace never removes a path outside the native prefix'

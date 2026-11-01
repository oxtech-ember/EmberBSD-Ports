#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). scripts/cross-bulk.sh must not replace a
# native package mid-pass when the new package drops a shared library that
# the installed one provides and installed packages depend on it: pkgsrc
# replace (pkg_add -U) would remove the library under them (OpenSSL 3 to 4
# removed libssl.3 under pkg_install). The native prefix of the test has
# ssl-3.0 (lib/libssl.3.dylib) and sqlite3-1.0 (lib/libsqlite3.0.dylib),
# both required by tool-1.0. The tree has ssl-4.0, which provides only
# lib/libssl.4.dylib, and sqlite3-1.0nb1, which keeps its library. Build
# must refuse the ssl replace (failed with reason replace, ssl-3.0 still
# installed, the log names the library and tool) and must still replace
# sqlite3.
# Usage: cross-bulk-native-replace-libraries.sh NEW_OUTPUT
set -eu
[ "$#" = 1 ] || { echo 'Usage: cross-bulk-native-replace-libraries.sh NEW_OUTPUT' >&2; exit 2; }
out=$1
case "$out" in /*) ;; *) echo 'NEW_OUTPUT must be absolute' >&2; exit 2 ;; esac
case "$out" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2 ;; esac
[ ! -e "$out" ] || exit 2
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
for p in t/a o/ssl s/sqlite3; do mkdir -p "$out/tree/$p"; done
mkdir -p "$out/packages/All" "$out/work" "$out/native-db" "$out/meta" "$out/vars"
L=/prefix/lib
: > "$out/native-db/ssl-3.0"
: > "$out/native-db/sqlite3-1.0"
: > "$out/native-db/tool-1.0"
# meta/PKGNAME.VARNAME: the build information lines of an installed package.
printf '%s\n' "$L/libssl.3.dylib" "$L/libcrypto.3.dylib" > "$out/meta/ssl-3.0.PROVIDES"
echo tool-1.0 > "$out/meta/ssl-3.0.REQUIRED_BY"
echo "$L/libsqlite3.0.dylib" > "$out/meta/sqlite3-1.0.PROVIDES"
echo tool-1.0 > "$out/meta/sqlite3-1.0.REQUIRED_BY"
printf '%s\n' "$L/libssl.3.dylib" "$L/libsqlite3.0.dylib" /usr/lib/libSystem.B.dylib > "$out/meta/tool-1.0.REQUIRES"
# vars/PKG.MODE.VARNAME holds a value; a missing file is empty.
v() { printf '%s\n' "$4" > "$out/vars/$1.$2.$3"; }
v a target PKGNAME a-1.0
v a target TOOL_DEPENDS 'ssl>=4.0:../../o/ssl sqlite3>=1.0nb1:../../s/sqlite3'
v ssl native PKGNAME ssl-4.0
v ssl native PROVIDES "$L/libssl.4.dylib $L/libcrypto.4.dylib"
v sqlite3 native PKGNAME sqlite3-1.0nb1
v sqlite3 native PROVIDES "$L/libsqlite3.0.dylib"
# pkg_info -K DB: -e PATTERN for BASE and BASE>=VERSION patterns, -q -Q VAR
# and -q -R of an installed package (by PKGNAME or PKGBASE) or of a package file.
cat > "$out/pkg_info" <<WRAP
#!/bin/sh
out=$out
db=\$2; shift 2
installed() {
    [ -e "\$db/\$1" ] && { echo "\$1"; return 0; }
    for f in "\$db/\$1"-[0-9]*; do [ -e "\$f" ] && { echo "\${f##*/}"; return 0; }; done
    return 1
}
case "\$1" in
-e)
    pattern=\$2
    case "\$pattern" in
        *'>='*) base=\${pattern%%>=*} want=\${pattern#*>=} ;;
        *) base=\$pattern want= ;;
    esac
    have=\$(installed "\$base") || exit 1
    have=\${have#"\$base"-}
    [ -z "\$want" ] && exit 0
    [ "\$(printf '%s\n%s\n' "\$want" "\$have" | sort -V | tail -n 1)" = "\$have" ] && exit 0
    exit 1 ;;
-q)
    case "\$2" in
        -Q) var=\$3 pkg=\$4 ;;
        -R) var=REQUIRED_BY pkg=\$3 ;;
        *) exit 2 ;;
    esac
    case "\$pkg" in
        /*) [ -f "\$pkg" ] || exit 1; sed -n "s/^\$var=//p" "\$pkg" ;;
        *) name=\$(installed "\$pkg") || exit 1; cat "\$out/meta/\$name.\$var" 2> /dev/null || true ;;
    esac ;;
*) exit 2 ;;
esac
WRAP
cat > "$out/bmake" <<WRAP
#!/bin/sh
out=$out
dir= target= varname= varnames= mode=target packages=
for a in "\$@"; do echo "\$a"; done | tr '\n' ' ' >> \$out/calls; echo >> \$out/calls
while [ "\$#" -gt 0 ]; do
    case "\$1" in
        -C) dir=\$2; shift 2 ;;
        VARNAME=*) varname=\${1#VARNAME=}; shift ;;
        VARNAMES=*) varnames=\${1#VARNAMES=}; shift ;;
        USE_CROSS_COMPILE=no) mode=native; shift ;;
        PACKAGES=*) packages=\${1#PACKAGES=}; shift ;;
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
    package)
        mkdir -p \$packages/All
        for l in \$(value PROVIDES); do echo "PROVIDES=\$l"; done > \$packages/All/\$(value PKGNAME).tgz ;;
    install|replace)
        name=\$(value PKGNAME) base=\$(value PKGBASE)
        for f in \$out/native-db/\$base-[0-9]*; do
            [ -e "\$f" ] || continue
            [ \$target = install ] && { echo "\$name: an older version is already installed"; exit 1; }
            old=\${f##*/}; rm -f "\$f"
            mv \$out/meta/\$old.REQUIRED_BY \$out/meta/\$name.REQUIRED_BY 2> /dev/null || true
            rm -f \$out/meta/\$old.PROVIDES
        done
        for l in \$(value PROVIDES); do echo "\$l"; done > \$out/meta/\$name.PROVIDES
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
grep -qx 'o/ssl@native' "$out/state/order" || fail "o/ssl@native is not in the order: $(cat "$out/state/order")"
: > "$out/calls"
bulk build "$out/state/order" "$out/state" > "$out/build.log" 2>&1 || true
[ -e "$out/native-db/ssl-3.0" ] && [ ! -e "$out/native-db/ssl-4.0" ] ||
    fail "ssl-4.0 replaced ssl-3.0, which removed libssl.3 under tool-1.0: $(ls "$out/native-db" | tr '\n' ' ')"
! grep -q '/o/ssl .* replace' "$out/calls" || fail 'the ssl replace ran'
grep -qx 'o/ssl@native replace' "$out/state/failed" ||
    fail "o/ssl@native is not failed with reason replace: $(cat "$out/state/failed")"
[ -f "$out/packages-native/All/ssl-4.0.tgz" ] || fail 'the ssl-4.0 package was not kept'
grep -q "$L/libssl.3.dylib" "$out/state/logs/o_ssl@native.log" &&
    grep -q "tool-1.0 (loads $L/libssl.3.dylib" "$out/state/logs/o_ssl@native.log" ||
    fail "the log does not name the library and its user: $(cat "$out/state/logs/o_ssl@native.log")"
[ -e "$out/native-db/sqlite3-1.0nb1" ] && [ ! -e "$out/native-db/sqlite3-1.0" ] ||
    fail "sqlite3, which keeps its library, was not replaced: $(ls "$out/native-db" | tr '\n' ' ')"
grep -q '^s/sqlite3@native ' "$out/state/done" || fail "s/sqlite3@native not done: $(cat "$out/state/done")"
echo 'PASS: a native replace that drops a library its dependents load is refused; one that keeps them runs'

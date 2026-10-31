#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). scripts/cross-bulk.sh build keeps the
# binary packages of native nodes out of the target repository. A target
# package t/x and its native node t/x@native have the same PKGNAME, and
# pkgsrc writes the binary package of either to PACKAGES/All. The
# recording bmake writes the mode into that file, as OPSYS in +BUILD_INFO
# would tell. The target package is built first; after the native node the
# target repository must still hold the target package, with the checksum
# that STATE/done recorded, and the native package must be in its own
# repository (PACKAGES-native).
# Usage: cross-bulk-native-packages.sh NEW_OUTPUT
set -eu
[ "$#" = 1 ] || { echo 'Usage: cross-bulk-native-packages.sh NEW_OUTPUT' >&2; exit 2; }
out=$1
case "$out" in /*) ;; *) echo 'NEW_OUTPUT must be absolute' >&2; exit 2 ;; esac
case "$out" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2 ;; esac
[ ! -e "$out" ] || exit 2
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
mkdir -p "$out/tree/t/x" "$out/packages/All" "$out/work" "$out/target-db" "$out/native-db"
cat > "$out/pkg_add" <<WRAP
#!/bin/sh
: > "\$2/\$3-1.0"
WRAP
cat > "$out/bmake" <<WRAP
#!/bin/sh
out=$out
echo "\$*" >> \$out/calls
dir= target= varname= add= mode=target packages=\$out/packages
while [ "\$#" -gt 0 ]; do
    case "\$1" in
        -C) dir=\$2; shift 2 ;;
        VARNAME=*) varname=\${1#VARNAME=}; shift ;;
        NATIVE_PKG_ADD_CMD=*) add=\${1#NATIVE_PKG_ADD_CMD=}; shift ;;
        USE_CROSS_COMPILE=no) mode=native; shift ;;
        PACKAGES=*) packages=\${1#PACKAGES=}; shift ;;
        *=*) shift ;;
        *) target=\$1; shift ;;
    esac
done
pkg=\${dir##*/}
case "\$target" in
    show-var)
        case "\$varname" in
            EMBERBSD_NATIVE_TOOLSET_VERIFIED) echo fake ;;
            PACKAGES) echo \$out/packages ;;
            PKG_INFO) echo "test -f \$out/native-db/x-1.0 #" ;;
            NATIVE_PKG_ADD_CMD) echo \$out/pkg_add ;;
            *) echo ;;
        esac ;;
    show-vars)
        if [ \$mode = native ]; then
            echo "\$pkg-1.0"; echo "\$out/work/\$pkg/work"; echo; echo "\$pkg"
        else
            echo "\$pkg-1.0"; echo "\$out/work/\$pkg/work.target"; echo
        fi ;;
    clean) ;;
    package-install|install)
        mkdir -p \$packages/All
        echo \$mode > \$packages/All/\$pkg-1.0.tgz
        if [ \$mode = native ]; then : > \$out/native-db/\$pkg-1.0; else \$add -K \$out/target-db \$pkg; fi ;;
    *) echo "bmake: don't know how to make \$target. Stop"; exit 2 ;;
esac
WRAP
chmod +x "$out/bmake" "$out/pkg_add"
fail() { echo "FAIL: $*" >&2; exit 1; }
mkdir "$out/state"
printf '%s\n' 't/x t/x' 't/x@native t/x@native' > "$out/state/edges"
printf '%s\n' t/x t/x@native > "$out/state/order"
: > "$out/calls"
BMAKE=$out/bmake MAKECONF=$out/mk.conf PKGSRCDIR=$out/tree CROSS_BULK_CPUS=1 CROSS_BULK_JOBS=1 \
    sh "$ports/scripts/cross-bulk.sh" build "$out/state/order" "$out/state" > "$out/bulk.log" 2>&1 ||
    fail "build: $(cat "$out/bulk.log")"
grep -q '^t/x x-1.0 ' "$out/state/done" || fail "t/x not done: $(cat "$out/state/done")"
grep -q '^t/x@native ' "$out/state/done" || fail "t/x@native not done: $(cat "$out/state/done")"
[ "$(cat "$out/packages/All/x-1.0.tgz")" = target ] ||
    fail "the native node replaced the target package x-1.0.tgz in PACKAGES/All"
grep -qx "t/x x-1.0 $(shasum -a 256 "$out/packages/All/x-1.0.tgz" | cut -d ' ' -f 1)" "$out/state/done" ||
    fail 'the target package no longer has the checksum in STATE/done'
[ "$(cat "$out/packages-native/All/x-1.0.tgz" 2> /dev/null)" = native ] ||
    fail 'the native package is not in PACKAGES-native/All'
echo 'PASS: native packages go to PACKAGES-native; the target repository keeps the target package'

#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). A cross package stops before it uses a
# cross libtool that was configured for other cross tools or another sysroot.
#
# A cross libtool records the absolute LD, NM and RANLIB and the library
# search path of the TOOLDIR and CROSS_DESTDIR it was configured with.
# Configurations that share one TOOLBASE share its installed
# cross-libtool-base, so a package of one configuration could use the
# tools and sysroot of another, including a directory that has since
# been removed. The check runs in the wrapper phase, before configure.
set -eu
[ "$#" -eq 3 ] || {
    echo "Usage: $0 PKGSRC MAKECONF NEW_WORK" >&2
    exit 2
}
: "${BMAKE:?Set the native bmake executable}"
pkgsrc=$1 conf=$2 out=$3
for path in "$@"; do
    case "$path" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2 ;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) echo 'Use paths without shell metacharacters' >&2; exit 2 ;; esac
done
[ ! -e "$out" ] || { echo "$out exists" >&2; exit 2; }
mkdir "$out"
fail() { echo "FAIL: $*" >&2; exit 1; }
recipe=$pkgsrc/devel/readline
bm() { "$BMAKE" -C "$recipe" MAKECONF="$conf" WRKOBJDIR="$out/work" "$@"; }

[ "$(bm -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] ||
    fail 'MAKECONF does not select a cross build'
[ -n "$(bm -V '${USE_LIBTOOL:Dyes}')" ] || fail 'devel/readline does not use libtool'
tooldir=$(bm -V '${TOOLDIR}')
sysroot=$(bm -V '${CROSS_DESTDIR}')
[ -n "$tooldir" ] && [ -n "$sysroot" ] || fail 'TOOLDIR or CROSS_DESTDIR is empty'
triplet=aarch64--netbsd
stale=$out/old-config

# Stand-ins for the installed cross libtool, with the lines it records.
write_libtool() { # file tools sysroot
    {
        echo '#! /bin/sh'
        echo "NM=\"$2/bin/$triplet-nm\""
        echo "RANLIB=\"$2/bin/$triplet-ranlib\""
        echo 'AR="'"$triplet"'-ar"'
        echo "sys_lib_search_path_spec=\"$3/usr/pkg/llvm/lib/clang/23 $3/usr/lib \""
        echo 'sys_lib_dlsearch_path_spec="/lib /usr/lib"'
        echo "LD=\"$2/bin/$triplet-ld\""
        echo 'LD=""'
        echo "LD=\"$2/bin/$triplet-ld\""
    } > "$1"
}
write_libtool "$out/current" "$tooldir" "$sysroot"
write_libtool "$out/other-tools" "$stale/tools" "$sysroot"
write_libtool "$out/other-sysroot" "$tooldir" "$stale/sysroot"
sed -e "s|^RANLIB=.*|RANLIB=\"$triplet-ranlib\"|" "$out/current" > "$out/bare-names"
{ sed -e '/^sys_lib_search_path_spec=/d' "$out/current"
  echo "sys_lib_search_path_spec=\"$sysroot/usr/lib $stale/sysroot/usr/lib \""; } \
    > "$out/mixed-sysroot"

check() { bm PKG_LIBTOOL="$out/$1" check-cross-libtool > "$out/$1.log" 2>&1; }
check current || fail "a cross libtool for this TOOLDIR and CROSS_DESTDIR is rejected: $(tail -1 "$out/current.log")"
check bare-names || fail 'a cross libtool that runs a tool by name is rejected'
for lt in other-tools other-sysroot mixed-sysroot; do
    ! check "$lt" || fail "the $lt cross libtool is accepted"
    grep -q "configured for other cross tools or another sysroot: *$stale/" "$out/$lt.log" ||
        fail "the $lt rejection does not name the other directory"
done
! check missing || fail 'a missing cross libtool is accepted'

# The cross wrapper phase runs the check; a native build does not.
bm -n PKG_LIBTOOL="$out/current" do-wrapper > "$out/wrapper.log" 2>&1 ||
    fail 'make -n do-wrapper failed'
grep -q 'configured for other cross tools' "$out/wrapper.log" ||
    fail 'the cross wrapper phase does not check the cross libtool'
bm -n USE_CROSS_COMPILE=no do-wrapper > "$out/native-wrapper.log" 2>&1 ||
    fail 'native make -n do-wrapper failed'
! grep -q 'configured for other cross tools' "$out/native-wrapper.log" ||
    fail 'a native wrapper phase checks the cross libtool'
echo 'PASS: cross packages reject a cross libtool configured for other cross tools or another sysroot'

#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). A cross package stops before it uses a
# cross libtool configured for other cross tools or another sysroot.
#
# The guard accepts only selected tool/sysroot roots, the exact bound Clang
# resource directory as a search path, and the canonical selected target
# runtime root as a search-path prefix. It rejects unrelated roots and aliases,
# except that a sysroot-kind runtime root may be the selected CROSS_DESTDIR link.
set -eu
[ "$#" -eq 3 ] || {
    echo "Usage: $0 PKGSRC MAKECONF NEW_WORK" >&2
    exit 2
}
: "${BMAKE:?Set the native bmake executable}"
pkgsrc=$1 conf=$2 out=$3
for path in "$@" ; do
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
selected=$(bm EMBERBSD_CROSS_LIBTOOL="$out/current" -V '${PKG_LIBTOOL}')
[ "$selected" = "$out/current" ] || fail 'cross MAKECONF ignores the selected target libtool'
native=$(bm USE_CROSS_COMPILE=no EMBERBSD_CROSS_LIBTOOL="$out/current" -V '${PKG_LIBTOOL}')
[ "$native" != "$out/current" ] || fail 'native dependencies inherit the target libtool'
tooldir=$(bm -V '${TOOLDIR}')
sysroot=$(bm -V '${CROSS_DESTDIR}')
runtime=$(bm -V '${_EMBER_TARGET_RUNTIME_ROOT:U}')
family=$(bm -V '${_EMBER_TARGET_FAMILY:U}')
triplet=$(bm -V '${_EMBER_CROSS_TRIPLET}')
selected_shell=$(bm -V '${SH:U}')
[ -n "$selected_shell" ] || selected_shell=$(bm -V '${TOOLS_SHELL:U}')
[ -x "$selected_shell" ] || fail 'selected test shell is missing'
[ -n "$tooldir" ] && [ -n "$sysroot" ] && [ -n "$triplet" ] ||
    fail 'TOOLDIR, CROSS_DESTDIR or target triplet is empty'
[ -n "$runtime" ] || fail 'selected target runtime root is missing'
[ -d "$runtime" ] || fail 'selected target runtime root does not exist'
kind=$(bm -V '${_EMBER_TARGET_RUNTIME_KIND:U}')
# A sysroot-kind runtime may keep the selected CROSS_DESTDIR spelling (the
# sysroot link of a prepare-libtool.py context); any other runtime root must
# be canonical.
if [ "$(CDPATH= cd "$runtime" && pwd -P)" != "$runtime" ]; then
    [ "$kind" = sysroot ] && [ "$runtime" = "$sysroot" ] ||
        fail 'selected target runtime root is not canonical'
fi
resource_dir=$sysroot/usr/pkg/llvm/lib/clang/23
if [ "$family" = clang ]; then
    clangbase=$(bm -V '${CLANGBASE}')
    [ "$clangbase" = "$tooldir" ] || fail 'CLANGBASE is not selected TOOLDIR'
    resource_dir=$("$clangbase/bin/clang" -print-resource-dir) ||
        fail 'selected Clang cannot report its resource directory'
    case "$resource_dir" in /*) ;; *) fail 'selected Clang resource path is not absolute' ;; esac
    case "$resource_dir" in *[[:space:]]*) fail 'selected Clang resource path has whitespace' ;; esac
fi
stale=$out/old-config

# Stand-ins retain repeated LD assignments and exercise tool fields separately
# from the library search-path allowlist.
write_libtool() {
    file=$1 tools=$2 libs=$3
    ld=${4:-$tools/bin/$triplet-ld}
    nm=${5:-$tools/bin/$triplet-nm}
    ranlib=${6:-$tools/bin/$triplet-ranlib}
    {
        echo '#! /bin/sh'
        echo "NM=\"$nm\""
        echo "RANLIB=\"$ranlib\""
        echo 'AR="'"$triplet"'-ar"'
        echo "sys_lib_search_path_spec=\"$libs\""
        echo 'sys_lib_dlsearch_path_spec="/lib /usr/lib"'
        echo "LD=\"$ld\""
        echo 'LD=""'
        echo "LD=\"$ld\""
    } > "$file"
}
write_libtool "$out/current" "$tooldir" "$sysroot/usr/lib $runtime/usr/pkg/llvm/lib $resource_dir"
write_libtool "$out/other-tools" "$stale/tools" "$sysroot/usr/lib $runtime/usr/pkg/llvm/lib $resource_dir"
write_libtool "$out/other-sysroot" "$tooldir" "$stale/sysroot/usr/lib"
write_libtool "$out/old-resource" "$tooldir" "$stale/runtime/lib/clang/23"
write_libtool "$out/tool-runtime" "$tooldir" "$sysroot/usr/lib" "$runtime/bin/$triplet-ld"
sed -e "s|^RANLIB=.*|RANLIB=\"$triplet-ranlib\"|" "$out/current" > "$out/bare-names"
{ sed -e '/^sys_lib_search_path_spec=/d' "$out/current"
  echo "sys_lib_search_path_spec=\"$resource_dir $sysroot/usr/lib $stale/sysroot/usr/lib \""; } \
    > "$out/mixed-sysroot"

check() { bm PKG_LIBTOOL="$out/$1" check-cross-libtool > "$out/$1.log" 2>&1; }
check current || fail "the selected libtool paths are rejected: $(tail -1 "$out/current.log")"
check bare-names || fail 'a cross libtool that runs a tool by name is rejected'
rejected='other-tools other-sysroot mixed-sysroot old-resource'
# Tools under CROSS_DESTDIR are selected tools, so a sysroot runtime root
# (which is CROSS_DESTDIR) has no separate runtime tool path to reject.
[ "$runtime" = "$sysroot" ] || rejected="$rejected tool-runtime"
for lt in $rejected; do
    ! check "$lt" || fail "the $lt cross libtool is accepted"
    grep -q 'configured for other cross tools or another sysroot:' "$out/$lt.log" ||
        fail "the $lt rejection does not identify invalid metadata"
done
ln -s "$runtime" "$out/runtime-link"
write_libtool "$out/runtime-alias" "$tooldir" "$sysroot/usr/lib" "$out/runtime-link/usr/pkg/llvm/lib"
! check runtime-alias || fail 'a symlink alias of the selected runtime root is accepted'
grep -Fq "$out/runtime-link/" "$out/runtime-alias.log" ||
    fail 'runtime symlink rejection does not name the alias path'
! check missing || fail 'a missing cross libtool is accepted'

if [ "$family" = clang ]; then
    for p in "${runtime}-sibling/usr/pkg/llvm/lib/clang/23" "$stale/runtime/lib/clang/23"; do
        write_libtool "$out/invalid-resource" "$tooldir" "$sysroot/usr/lib $p"
        ! check invalid-resource || fail 'an unselected runtime/resource path is accepted'
    done
    # A resource directory inside CROSS_DESTDIR is already a selected tool root.
    case "$resource_dir" in "$sysroot"/*) ;; *)
    write_libtool "$out/tool-resource" "$tooldir" "$sysroot/usr/lib" "$resource_dir/bin/$triplet-ld"
    ! check tool-resource || fail 'the Clang resource directory is accepted for executable tools'
    ;; esac
fi

# The cross wrapper phase runs the check; a native build does not.
bm -n PKG_LIBTOOL="$out/current" do-wrapper > "$out/wrapper.log" 2>&1 ||
    fail 'make -n do-wrapper failed'
grep -q 'configured for other cross tools' "$out/wrapper.log" ||
    fail 'the cross wrapper phase does not check the cross libtool'
bm -n USE_CROSS_COMPILE=no do-wrapper > "$out/native-wrapper.log" 2>&1 ||
    fail 'native make -n do-wrapper failed'
! grep -q 'configured for other cross tools' "$out/native-wrapper.log" ||
    fail 'a native wrapper phase checks the cross libtool'
echo 'PASS: cross libtool accepts only selected tools, sysroot, exact resource dir, and canonical runtime search paths'

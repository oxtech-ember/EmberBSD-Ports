#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). A cross package stops before it uses a
# cross libtool configured for other cross tools or another sysroot.
#
# Prepared Clang may record its exact bound resource directory as a search
# path. The guard queries the verified TOOLDIR compiler and permits that
# exact search entry only; it never permits a tool field to use the resource.
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
tooldir=$(bm -V '${TOOLDIR}')
sysroot=$(bm -V '${CROSS_DESTDIR}')
family=$(bm -V '${_EMBER_TARGET_FAMILY:U}')
triplet=$(bm -V '${_EMBER_CROSS_TRIPLET}')
selected_shell=$(bm -V '${SH:U}')
[ -n "$selected_shell" ] || selected_shell=$(bm -V '${TOOLS_SHELL:U}')
[ -x "$selected_shell" ] || fail 'selected test shell is missing'
[ -n "$tooldir" ] && [ -n "$sysroot" ] && [ -n "$triplet" ] ||
    fail 'TOOLDIR, CROSS_DESTDIR or target triplet is empty'
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

# Stand-ins retain the historical empty and repeated LD assignments. The
# guard checks every recorded tool value but grants the resource exception
# only to the library search-path field.
write_libtool() { # file tools sysroot resource [ld [nm [ranlib]]]
    ld=$2/bin/$triplet-ld; [ "$#" -lt 5 ] || ld=$5
    nm=$2/bin/$triplet-nm; [ "$#" -lt 6 ] || nm=$6
    ranlib=$2/bin/$triplet-ranlib; [ "$#" -lt 7 ] || ranlib=$7
    {
        echo '#! /bin/sh'
        echo "NM=\"$nm\""
        echo "RANLIB=\"$ranlib\""
        echo 'AR="'"$triplet"'-ar"'
        echo "sys_lib_search_path_spec=\"$4 $3/usr/lib \""
        echo 'sys_lib_dlsearch_path_spec="/lib /usr/lib"'
        echo "LD=\"$ld\""
        echo 'LD=""'
        echo "LD=\"$ld\""
    } > "$1"
}
write_libtool "$out/current" "$tooldir" "$sysroot" "$resource_dir"
write_libtool "$out/other-tools" "$stale/tools" "$sysroot" "$resource_dir"
write_libtool "$out/other-sysroot" "$tooldir" "$stale/sysroot" "$resource_dir"
write_libtool "$out/old-resource" "$tooldir" "$sysroot" "$stale/runtime/lib/clang/23"
sed -e "s|^RANLIB=.*|RANLIB=\"$triplet-ranlib\"|" "$out/current" > "$out/bare-names"
{ sed -e '/^sys_lib_search_path_spec=/d' "$out/current"
  echo "sys_lib_search_path_spec=\"$resource_dir $sysroot/usr/lib $stale/sysroot/usr/lib \""; } \
    > "$out/mixed-sysroot"

check() { bm PKG_LIBTOOL="$out/$1" check-cross-libtool > "$out/$1.log" 2>&1; }
check current || fail "the selected libtool paths are rejected: $(tail -1 "$out/current.log")"
check bare-names || fail 'a cross libtool that runs a tool by name is rejected'
for lt in other-tools other-sysroot mixed-sysroot; do
    ! check "$lt" || fail "the $lt cross libtool is accepted"
    grep -q 'configured for other cross tools or another sysroot:' "$out/$lt.log" ||
        fail "the $lt rejection does not identify invalid metadata"
done
! check old-resource || fail 'an old or unselected resource directory is accepted'

if [ "$family" = clang ]; then
    write_libtool "$out/resource-sibling" "$tooldir" "$sysroot" "$resource_dir-sibling"
    write_libtool "$out/resource-lookalike" "$tooldir" "$sysroot" "${resource_dir}0"
    write_libtool "$out/tool-resource-ld" "$tooldir" "$sysroot" "$resource_dir" \
        "$resource_dir/bin/$triplet-ld"
    write_libtool "$out/tool-resource-nm" "$tooldir" "$sysroot" "$resource_dir" \
        "$tooldir/bin/$triplet-ld" "$resource_dir/bin/$triplet-nm"
    write_libtool "$out/tool-resource-ranlib" "$tooldir" "$sysroot" "$resource_dir" \
        "$tooldir/bin/$triplet-ld" "$tooldir/bin/$triplet-nm" "$resource_dir/bin/$triplet-ranlib"
    for lt in resource-sibling resource-lookalike tool-resource-ld tool-resource-nm tool-resource-ranlib; do
        ! check "$lt" || fail "$lt cross libtool is accepted"
        grep -q 'configured for other cross tools or another sysroot:' "$out/$lt.log" ||
            fail "$lt rejection does not identify invalid metadata"
    done

    query_tools=$out/query-tools
    mkdir -p "$query_tools/bin"
    sed "s|^_EMBER_TARGET_TOOLS:= .*|_EMBER_TARGET_TOOLS:= $query_tools|" \
        "$tooldir/target.mk" > "$query_tools/target.mk"
    {
        printf '#!%s\n' "$selected_shell"
        printf 'exit 9\n'
    } > "$query_tools/bin/clang"
    chmod +x "$query_tools/bin/clang"
    ! bm TOOLDIR="$query_tools" PKG_LIBTOOL="$out/current" check-cross-libtool \
        > "$out/query-failed.log" 2>&1 ||
        fail 'a failed prepared-Clang resource query is accepted'
    grep -q 'Could not query the selected Clang resource directory' "$out/query-failed.log" ||
        fail 'resource-query failure did not stop the guard explicitly'
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
echo 'PASS: cross packages reject mismatched libtool paths; prepared Clang permits only its exact resource search path'

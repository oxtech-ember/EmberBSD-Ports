#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check target libtool names the cross family's compiler.
set -eu
[ "$#" -eq 4 ] || {
    echo "Usage: $0 PKGSRC MAKECONF CLANG_CONFIGURED_LIBTOOL NEW_OUTPUT" >&2
    exit 2
}
: "${BMAKE:?Set the native bmake executable}"
pkgsrc=$1 conf=$2 configured=$3 out=$4
for path in "$@"; do
    case "$path" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2 ;; esac
    case "$path" in *[!A-Za-z0-9_./-]*) echo 'Use paths without shell metacharacters' >&2; exit 2 ;; esac
done
mkdir "$out"
field() { sed -n "s/^$1=//p" "$2"; }
fail() { echo "FAIL: $*" >&2; exit 1; }
recipe() {
    family=$1; shift
    "$BMAKE" -C "$pkgsrc/devel/libtool-base" MAKECONF="$conf" \
        EMBERBSD_CROSS_COMPILER_FAMILY="$family" WRKOBJDIR="$out/work" "$@"
}
convert() {
    family=$1 dir=$out/$1
    mkdir -p "$dir/src" "$dir/wrk"
    recipe "$family" -V 'FAIL=${PKG_FAIL_REASON}' -V 'PREFIX=${PREFIX}' \
        -V 'SYSROOT=${CROSS_DESTDIR}' -V 'TRIPLET=${MACHINE_GNU_PLATFORM}' \
        > "$dir/metadata.log"
    reason=$(field FAIL "$dir/metadata.log")
    case "$family:$reason" in
        *:) ;;
        # A Clang sysroot lacks the GCC16 runtime; the conversion does not read it.
        gcc:*GCC16*) echo "NOTE: gcc override refusal ignored: $reason" ;;
        *) fail "$family metadata rejected: $reason" ;;
    esac
    prefix=$(field PREFIX "$dir/metadata.log")
    sysroot=$(field SYSROOT "$dir/metadata.log")
    triplet=$(field TRIPLET "$dir/metadata.log")
    [ -n "$sysroot" ] && [ -n "$triplet" ] || fail "$family is not a cross build"
    grep -q "^sys_lib_search_path_spec=\"$sysroot/" "$configured" ||
        fail 'fixture is not a sysroot-configured libtool'
    grep -q "$triplet-clang" "$configured" || fail 'fixture does not name the Clang cross driver'
    mkdir -p "$dir/destdir$prefix/bin"
    cp "$configured" "$dir/src/shlibtool"
    for f in libtool libtoolize; do cp "$configured" "$dir/destdir$prefix/bin/$f"; done
    recipe "$family" DESTDIR="$dir/destdir" WRKSRC="$dir/src" WRKDIR="$dir/wrk" \
        ember-target-libtool > "$dir/convert.log" 2>&1 ||
        { cat "$dir/convert.log" >&2; fail "$family conversion failed"; }
    target=$dir/destdir$prefix/bin/libtool
}

convert clang
for f in libtool libtoolize shlibtool; do
    script=$out/clang/destdir$prefix/bin/$f
    ! grep -n gcc16 "$script" || fail "clang $f names the GCC16 compiler"
    ! grep -n "$triplet-" "$script" || fail "clang $f keeps a host cross tool"
done
grep -q "^LTCC=\"$prefix/bin/clang[ \"]" "$target" || fail 'LTCC is not target clang'
grep -q "^CC=\"$prefix/bin/clang[ \"]" "$target" || fail 'C tag is not target clang'
grep -q "^CC=\"$prefix/bin/clang++[ \"]" "$target" || fail 'CXX tag is not target clang++'
search=$(grep '^sys_lib_search_path_spec=' "$target")
case "$search" in
    *"$sysroot"*) fail 'search path keeps the build sysroot' ;;
    'sys_lib_search_path_spec="/usr/pkg/llvm/lib/clang/'*) ;;
    *) fail "unexpected clang search path: $search" ;;
esac

convert gcc
grep -qx "sys_lib_search_path_spec=\"/usr/pkg/gcc16/lib/gcc/$triplet/16.2.0 /usr/pkg/gcc16/lib /usr/lib /lib\"" \
    "$target" || fail 'gcc override lost the GCC16 runtime search path'
echo PASS

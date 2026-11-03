#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# Exercise host ABI containment using selected Clang and actual ELF libraries.
set -eu
[ "$#" -eq 8 ] || {
    echo 'usage: native-shlibs-host-abi.sh PKGSRC PATCH CC LD READELF AWK SYSTEM_RPATH WORK_PARENT' >&2
    exit 2
}
pkgsrc=$1 patchcmd=$2 cc=$3 ld=$4 readelf=$5 awkcmd=$6 system_rpath=$7 work_parent=$8
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd -P)
w=$(mktemp -d "$work_parent/native-shlibs.XXXXXX")
trap 'rm -rf "$w"' EXIT HUP INT TERM
mkdir -p "$w/mk/check" "$w/stage/usr/bin" "$w/allowed/lib" "$w/foreign" "$w/target" "$w/object-work"
cp "$pkgsrc/mk/check/check-shlibs-elf.awk" "$w/mk/check/"
cp "$pkgsrc/mk/check/check-shlibs.mk" "$w/mk/check/"
"$patchcmd" -s -p1 -d "$w" < "$root/profiles/common-build-tools/patches/native-check-shlibs-host-abi.patch"
printf 'int probe(void){return 0;}\n' > "$w/lib.c"
printf 'extern int probe(void); int main(void){return probe();}\n' > "$w/main.c"
"$cc" -shared -fPIC "-fuse-ld=$ld" "$w/lib.c" -o "$w/allowed/lib/libprobe.so"
cp "$w/allowed/lib/libprobe.so" "$w/foreign/libprobe.so"
for kind in allowed foreign; do
    dir="$w/$kind"
    [ "$kind" != allowed ] || dir="$w/allowed/lib"
    "$cc" "-fuse-ld=$ld" "$w/main.c" -L"$dir" -lprobe -Wl,-rpath,"$dir" -o "$w/stage/usr/bin/$kind"
done
for kind in allowed foreign cross disabled; do
    bin="$w/stage/usr/bin/$kind"
    cross= flag=yes
    case "$kind" in
      cross) bin="$w/stage/usr/bin/allowed"; cross="$w/target";;
      disabled) bin="$w/stage/usr/bin/allowed"; flag=no;;
    esac
    result=$(printf '%s\n' "$bin" | env PLATFORM_RPATH="$system_rpath" PREFIX="$w/allowed" \
        DESTDIR="$w/stage" CROSS_DESTDIR="$cross" EMBERBSD_NATIVE_HOST_ABI="$flag" \
        READELF="$readelf" PKG_INFO_CMD=/bin/false DEPENDS_FILE=/dev/null WRKDIR="$w/object-work" \
        "$awkcmd" -f "$w/mk/check/check-shlibs-elf.awk")
    case "$kind" in
      allowed) [ -z "$result" ] || { echo "$result" >&2; exit 1; };;
      foreign) printf '%s\n' "$result" | grep -q 'missing library: libprobe.so';;
      *) printf '%s\n' "$result" | grep -q 'missing library: libc.so.6';;
    esac
done
echo 'PASS: native prefix/system ABI resolution; foreign RPATH and cross host fallback denied'

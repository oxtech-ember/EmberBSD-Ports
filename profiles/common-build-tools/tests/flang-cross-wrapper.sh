#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD, AI-assisted regression for the Clang-profile Fortran path.
# Usage: MAKECONF=CROSS_MK_CONF BMAKE=BMAKE flang-cross-wrapper.sh EXPORTED_PKGSRC NEW_WORK [PKGPATH]
# The Clang cross profile compiles Fortran with the build-host Flang and links
# Flang-RT from the target sysroot. The test generates the real cwrappers of a
# Fortran recipe, then compiles and links a program and a shared library
# through the generated wrapper. It fails when the profile selects GCC, when
# the driver is run from the host prefix (its lib directory joins the link),
# when the link does not use the selected cross ld, or when a build-host
# library directory reaches the link line or the produced objects.
# Flang-RT must already be installed in the target sysroot.
set -eu
[ "$#" -ge 2 ] && [ "$#" -le 3 ] || {
    echo "Usage: MAKECONF=CROSS_MK_CONF BMAKE=BMAKE $0 EXPORTED_PKGSRC NEW_WORK [PKGPATH]" >&2; exit 2; }
pkgsrc=$(CDPATH= cd -- "$1" && pwd)
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
pkgpath=${3:-math/blas}
make=${BMAKE:?set BMAKE to the selected bmake}
dir=$pkgsrc/$pkgpath
fail() { echo "FAIL: $*" >&2; exit 1; }
mk() { "$make" -C "$dir" WRKOBJDIR="$work/obj" "$@"; }
names='PKG_FAIL_REASON FC DEPENDS BUILD_DEPENDS TOOL_DEPENDS EMBERBSD_FLANG PKG_FC LD
    TOOLBASE CROSS_DESTDIR CWRAPPERS_CONFIG_DIR WRAPPER_BINDIR _EMBER_FLANG_RT
    MACHINE_GNU_PLATFORM'
set --
for n in $names; do set -- "$@" -V "\${$n}"; done
mk "$@" > "$work/vars" || fail "cannot query $pkgpath"
i=0
while IFS= read -r line; do
    i=$((i + 1)); n=$(echo $names | cut -d' ' -f$i)
    eval "v_$n=\$line"
done < "$work/vars"
[ "$i" -eq "$(echo $names | wc -w)" ] || fail "unexpected make query output"
[ -z "$v_PKG_FAIL_REASON" ] || fail "$pkgpath: $v_PKG_FAIL_REASON"
[ "$v_FC" = flang ] || fail "FC is $v_FC, not flang"
case " $v_DEPENDS $v_BUILD_DEPENDS $v_TOOL_DEPENDS " in
*gcc*) fail "the dependencies name GCC: $v_DEPENDS $v_BUILD_DEPENDS $v_TOOL_DEPENDS";;
esac
flang=$v_EMBERBSD_FLANG pkgfc=$v_PKG_FC ld=$v_LD toolbase=$v_TOOLBASE
sysroot=$v_CROSS_DESTDIR cfg=$v_CWRAPPERS_CONFIG_DIR bin=$v_WRAPPER_BINDIR
rtlib=$v__EMBER_FLANG_RT/lib/$v_MACHINE_GNU_PLATFORM
case $rtlib in "$sysroot"/*) ;; *) fail "Flang-RT $rtlib is outside the sysroot";; esac
case $ld in /*) [ -x "$ld" ] || fail "LD $ld is not executable";; *) fail "LD $ld is not absolute";; esac

mk "$pkgfc" >/dev/null || fail "cannot stage the package Flang driver"
[ ! -L "$pkgfc" ] || fail "$pkgfc is a symbolic link; the driver would resolve to the host prefix"
[ "$(ls -i "$pkgfc" | awk '{print $1}')" = "$(ls -i "$flang" | awk '{print $1}')" ] ||
    cmp -s "$pkgfc" "$flang" || fail "$pkgfc is not the selected Flang"
[ ! -e "${pkgfc%/bin/*}/lib" ] || fail "the staged driver has a lib directory beside it"
mkdir -p "$cfg" "$bin"
mk WRAPPER_TARGETS= generate-cwrappers >/dev/null || fail "cannot generate the cwrappers"
[ -x "$bin/flang" ] || fail "cwrappers do not wrap the flang command name"
grep -qxF "exec=$pkgfc" "$cfg/f77" || fail "the f77 wrapper does not run $pkgfc"
for k in append_executable append_shared; do
    grep -qxF "$k=-fuse-ld=$ld" "$cfg/f77" || fail "$k lacks -fuse-ld=$ld"
done

cat > "$work/hello.f90" <<'F90'
program hello
  use iso_fortran_env, only: output_unit
  write (output_unit, '(a)') 'flang wrapper'
end program hello
F90
cat > "$work/shared.f90" <<'F90'
subroutine hello(n)
  integer :: n
  print *, 'flang shared ', n
end subroutine hello
F90
export CWRAPPERS_CONFIG_DIR="$cfg"
cd "$work"
"$bin/flang" -c hello.f90 2>compile.err || { cat compile.err >&2; fail "wrapped compile failed"; }
[ ! -s compile.err ] || { cat compile.err >&2; fail "wrapped compile warned"; }
"$bin/flang" -### -o hello hello.o 2>link.txt || fail "wrapped link dry run failed"
"$bin/flang" -o hello hello.o || fail "wrapped link failed"
"$bin/flang" -shared -o libhello.so shared.f90 2>shared.err || { cat shared.err >&2; fail "wrapped shared link failed"; }
grep -qF "\"$ld\"" link.txt || fail "the link does not run $ld"
grep -qF -- "-lflang_rt.runtime" link.txt || fail "the link does not use Flang-RT"
tr ' ' '\n' < link.txt | grep -qxF "\"-L$rtlib\"" || fail "the link does not search the sysroot Flang-RT directory"
for leak in "$toolbase/lib" "${flang%/bin/*}/lib" /opt/homebrew /usr/local /Applications \
    /Library/Developer /System gcc gfortran; do
    ! grep -F -- "$leak" link.txt || fail "the link line names $leak"
done
case $(file -b hello) in ELF*64-bit*aarch64*) ;; *) fail "hello is $(file -b hello)";; esac
case $(file -b libhello.so) in ELF*64-bit*shared\ object*aarch64*) ;; *) fail "libhello.so is $(file -b libhello.so)";; esac
for f in hello libhello.so; do
    "$toolbase/bin/llvm-readelf" -d "$f" > "$f.dyn" || fail "cannot read $f"
    ! grep -E 'RUNPATH|RPATH' "$f.dyn" | grep -F -e "$toolbase" -e "$sysroot" -e /Users -e /Volumes ||
        fail "$f records a build-host run path"
    ! grep NEEDED "$f.dyn" | grep -E 'gfortran|quadmath|libgcc' || fail "$f needs a GCC runtime"
done
echo "PASS: Clang-profile Fortran compiles and links with host Flang, sysroot Flang-RT and $ld"

#!/bin/sh
# Causal test for lang/flang-rt: a cross Fortran program that uses the
# intrinsic modules and the runtime must compile and link against the
# installed package alone, and a Fortran shared library must link the
# runtime.  Without flang-rt the module lookup or the link fails; a
# runtime built without PIC fails the shared link.
#
# Usage: cross-link.sh FLANG LD SYSROOT RESOURCE_DIR TARGET
#   RESOURCE_DIR is the installed ${PREFIX}/lib/clang/<major> tree.
set -eu

if [ "$#" -ne 5 ]; then
	echo "usage: $0 FLANG LD SYSROOT RESOURCE_DIR TARGET" >&2
	exit 2
fi
flang=$1 ld=$2 sysroot=$3 res=$4 target=$5

work=$(mktemp -d "${TMPDIR:-/tmp}/flang-rt-test.XXXXXX")
trap 'rm -rf "$work"' EXIT

cat > "$work/hello.f90" <<'F90'
program hello
  use iso_c_binding, only: c_int
  use iso_fortran_env, only: output_unit
  integer(c_int) :: i, s
  s = 0
  do i = 1, 6
    s = s + i
  end do
  write (output_unit, '(a,i0)') 'flang sum ', s * 2
end program hello
F90

for f in "$res/lib/$target/libflang_rt.runtime.a" \
    "$res/finclude/flang/$target/iso_c_binding.mod"; do
	if [ ! -f "$f" ]; then
		echo "FAIL: missing $f" >&2
		exit 1
	fi
done

if ! "$flang" --target="$target" --sysroot="$sysroot" \
    -fuse-ld="$ld" \
    -fintrinsic-modules-path="$res/finclude/flang/$target" \
    -L"$res/lib/$target" \
    -o "$work/hello" "$work/hello.f90"; then
	echo "FAIL: cross compile or link failed" >&2
	exit 1
fi

case $(file -b "$work/hello") in
ELF*64-bit*ARM\ aarch64*|ELF*64-bit*aarch64*) ;;
*)
	echo "FAIL: unexpected output: $(file -b "$work/hello")" >&2
	exit 1
	;;
esac
cat > "$work/shared.f90" <<'F90'
subroutine hello(n)
  integer :: n
  print *, 'flang shared ', n
end subroutine hello
F90
if ! "$flang" --target="$target" --sysroot="$sysroot" \
    -fuse-ld="$ld" -fPIC -shared \
    -L"$res/lib/$target" \
    -o "$work/libhello.so" "$work/shared.f90"; then
	echo "FAIL: cross Fortran shared library link failed" >&2
	exit 1
fi
case $(file -b "$work/libhello.so") in
ELF*64-bit*shared\ object*aarch64*) ;;
*)
	echo "FAIL: unexpected shared output: $(file -b "$work/libhello.so")" >&2
	exit 1
	;;
esac
echo "PASS: cross Fortran program and shared library link against flang-rt"

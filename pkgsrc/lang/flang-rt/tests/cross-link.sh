#!/bin/sh
# Causal test for lang/flang-rt: Fortran programs and shared libraries link
# the one installed shared runtime, so libraries loaded together share its
# state.  Library A opens a unit and library B inquires it; that works only
# if both use the same runtime copy.  The ELF check proves it at link level:
# A, B and the program need the versioned runtime, and neither library
# defines runtime entry points of its own.  A static or PIC-archive runtime
# fails this check, as does a missing or unversioned shared runtime.
#
# Usage: cross-link.sh FLANG LD SYSROOT RESOURCE_DIR LIBDIR TARGET READELF NM
#   RESOURCE_DIR is the installed ${PREFIX}/lib/clang/<major> tree and
#   LIBDIR the installed ${PREFIX}/lib.
set -eu

if [ "$#" -ne 8 ]; then
	echo "usage: $0 FLANG LD SYSROOT RESOURCE_DIR LIBDIR TARGET READELF NM" >&2
	exit 2
fi
flang=$1 ld=$2 sysroot=$3 res=$4 libdir=$5 target=$6 readelf=$7 nm=$8

work=$(mktemp -d "${TMPDIR:-/tmp}/flang-rt-test.XXXXXX")
trap 'rm -rf "$work"' EXIT

fail() {
	echo "FAIL: $*" >&2
	exit 1
}

major=${res##*/}
soname=libflang_rt.runtime.so.$major
for f in "$libdir/$soname" "$libdir/libflang_rt.runtime.so" \
    "$res/finclude/flang/$target/iso_c_binding.mod"; do
	[ -e "$f" ] || fail "missing $f"
done
for f in "$res/lib/$target/libflang_rt.runtime.a" \
    "$libdir/libflang_rt.runtime.a"; do
	[ ! -e "$f" ] || fail "static runtime installed: $f"
done
"$readelf" -d "$libdir/$soname" | grep -q "(SONAME).*\\[$soname\\]" ||
	fail "runtime SONAME is not $soname"

fc() {
	"$flang" --target="$target" --sysroot="$sysroot" -fuse-ld="$ld" \
	    -fintrinsic-modules-path="$res/finclude/flang/$target" \
	    -L"$libdir" "$@"
}

cat > "$work/a.f90" <<'F90'
subroutine open_shared_unit()
  open (unit=42, status='scratch', form='formatted')
  write (42, '(a)') 'flang shared runtime'
end subroutine open_shared_unit
F90
cat > "$work/b.f90" <<'F90'
logical function shared_unit_open()
  inquire (unit=42, opened=shared_unit_open)
end function shared_unit_open
F90
cat > "$work/main.f90" <<'F90'
program shared_runtime
  use iso_fortran_env, only: output_unit
  logical, external :: shared_unit_open
  call open_shared_unit()
  if (.not. shared_unit_open()) error stop 'unit 42 is not shared'
  write (output_unit, '(a)') 'flang shared runtime ok'
end program shared_runtime
F90

fc -fPIC -shared -o "$work/liba.so" "$work/a.f90" ||
	fail "cross Fortran shared library A link failed"
fc -fPIC -shared -o "$work/libb.so" "$work/b.f90" ||
	fail "cross Fortran shared library B link failed"
fc -o "$work/main" "$work/main.f90" -L"$work" -la -lb ||
	fail "cross Fortran program link failed"

for o in liba.so libb.so main; do
	case $(file -b "$work/$o") in
	ELF*64-bit*aarch64*) ;;
	*) fail "unexpected $o: $(file -b "$work/$o")" ;;
	esac
	"$readelf" -d "$work/$o" | grep -q "(NEEDED).*\\[$soname\\]" ||
		fail "$o does not need $soname"
done
for o in liba.so libb.so; do
	if "$nm" -D --defined-only "$work/$o" | grep -q ' _Fortran'; then
		fail "$o carries its own Fortran runtime copy"
	fi
done
"$nm" -D --defined-only "$libdir/$soname" |
    grep -q ' _FortranAioInquireOpened$\| _FortranAioBeginOpenUnit$' ||
	fail "$soname does not define the I/O unit entry points"
echo "PASS: Fortran libraries and program share the one $soname"

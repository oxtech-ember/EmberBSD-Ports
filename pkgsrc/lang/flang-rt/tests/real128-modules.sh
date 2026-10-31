#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# The intrinsic modules that Flang-RT installs for an AArch64 ELF target
# give ISO_FORTRAN_ENV's REAL128 as kind 16. The modules record the kinds
# the building Flang enabled for the target, so modules built by a Flang
# without REAL(16) for that target name REAL128 as -1, and programs such as
# MPICH's mpi_f08 stop with "REAL(KIND=-1) is not a supported type".
# Usage: real128-modules.sh FLANG RESOURCE_DIR TARGET
#   RESOURCE_DIR is the installed ${PREFIX}/lib/clang/<major> tree.
set -eu
[ "$#" = 3 ] || { echo 'usage: real128-modules.sh FLANG RESOURCE_DIR TARGET' >&2; exit 2; }
flang=$1 res=$2 target=$3
mods=$res/finclude/flang/$target
[ -e "$mods/iso_fortran_env.mod" ] || { echo "no iso_fortran_env.mod in $mods" >&2; exit 2; }
work=$(mktemp -d "${TMPDIR:-/tmp}/flang-rt-real128.XXXXXX")
trap 'rm -rf "$work"' EXIT
cat > "$work/r128.f90" <<'F'
subroutine r128(a, b)
  use iso_fortran_env, only: real128
  real(real128), intent(in) :: a
  real(real128), intent(out) :: b
  integer, parameter :: k16(merge(1, 0, real128 == 16)) = 16
  b = a * 2.0_real128 + real(size(k16), real128)
end subroutine r128
F
if ! "$flang" --no-default-config --target="$target" \
    -fintrinsic-modules-path="$mods" -c -o "$work/r128.o" "$work/r128.f90" \
    > "$work/log" 2>&1; then
	sed -n 1,4p "$work/log"
	echo "FAIL: ISO_FORTRAN_ENV REAL128 is not kind 16 for $target"; exit 1
fi
echo "PASS: REAL128 is kind 16 in the $target modules"

#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# Compile, link and run a trivial Fortran program with a flang installed
# from this recipe, against a flang-rt runtime library directory. Also
# require that no shared library in the flang prefix carries its own copy
# of MLIR: MLIR is packaged as static libraries only, so linking it into
# several flang shared libraries duplicates its global registries, and
# flang crashes while it registers the MLIR dialects.
# Usage: NM=llvm-nm compile-run.sh FLANG_PREFIX FLANG_RT_LIBDIR NEW_WORK
set -eu
[ "$#" = 3 ] || { echo 'usage: NM=llvm-nm compile-run.sh FLANG_PREFIX FLANG_RT_LIBDIR NEW_WORK' >&2; exit 2; }
prefix=$1 rtlib=$2 work=$3
nm=${NM:-llvm-nm}
for p in "$prefix" "$rtlib" "$work"; do
	case "$p" in /*) ;; *) echo "not absolute: $p" >&2; exit 2 ;; esac
done
[ -x "$prefix/bin/flang" ] || { echo "no flang in $prefix" >&2; exit 2; }
ls "$rtlib"/libflang_rt.runtime.* > /dev/null 2>&1 || { echo "no flang-rt runtime in $rtlib" >&2; exit 2; }
[ ! -e "$work" ] || { echo "work must be new: $work" >&2; exit 2; }
mkdir "$work"
fail=0
for f in "$prefix"/lib/*.so "$prefix"/lib/*.so.* "$prefix"/lib/*.dylib; do
	[ -f "$f" ] && [ ! -h "$f" ] || continue
	case "$f" in */libMLIR-C.*) continue ;; esac
	if "$nm" --defined-only -C "$f" 2>/dev/null | grep -q 'mlir::MLIRContext::MLIRContext('; then
		echo "FAIL: shared library carries a copy of MLIR: ${f##*/}"; fail=1
	fi
done
cat > "$work/hello.f90" <<'F'
program hello
  integer :: i, s
  s = 0
  do i = 1, 6
    s = s + i
  end do
  print '(a,i0)', 'flang sum ', s * 2
end program hello
F
if ! "$prefix/bin/flang" -o "$work/hello" "$work/hello.f90" -L"$rtlib" > "$work/compile.log" 2>&1; then
	tail -n 5 "$work/compile.log"; echo 'FAIL: compile and link'; exit 1
fi
out=$("$work/hello") || { echo 'FAIL: the program did not run'; exit 1; }
[ "$out" = 'flang sum 42' ] || { echo "FAIL: unexpected output: $out"; fail=1; }
[ "$fail" = 0 ] || exit 1
echo 'PASS: flang compiles, links and runs a Fortran program'

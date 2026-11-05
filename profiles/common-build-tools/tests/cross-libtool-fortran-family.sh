#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); GCC cross profiles do not use Flang-RT.
# Usage: BMAKE=BMAKE cross-libtool-fortran-family.sh EXPORTED_PKGSRC NEW_WORK
set -eu
[ "$#" -eq 2 ] || { echo "Usage: BMAKE=BMAKE $0 EXPORTED_PKGSRC NEW_WORK" >&2; exit 2; }
pkgsrc=$(CDPATH= cd -- "$1" && pwd)
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
make=${BMAKE:?set BMAKE to the selected bmake}
dir=$pkgsrc/cross/cross-libtool-fortran
fail() { echo "FAIL: $*" >&2; exit 1; }
query() {
	"$make" -C "$dir" WRKOBJDIR="$work/obj" \
	    EMBERBSD_CROSS_COMPILER_FAMILY="$1" -V '${CROSS_TARGET_DEPENDS}'
}
clang=$(query clang) || fail "cannot query Clang cross recipe"
case " $clang " in *" flang-rt>="*":../../lang/flang-rt "*) ;; *) fail "Clang misses target Flang-RT: $clang";; esac
gcc=$(query gcc) || fail "cannot query GCC cross recipe"
[ -z "$gcc" ] || fail "GCC unexpectedly depends on Flang-RT: $gcc"
echo "PASS: Clang has the target Flang-RT edge; GCC has none"

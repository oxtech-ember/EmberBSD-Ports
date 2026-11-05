#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); fake-cross Fortran follows the target family.
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
	    USE_CROSS_COMPILE=yes TOOLS_USE_CROSS_COMPILE=no \
	    EMBERBSD_HOST_COMPILER_FAMILY=clang EMBERBSD_CROSS_COMPILER_FAMILY="$1" \
	    PKGSRC_COMPILER=clang \
	    -V '${FC}' -V '${TOOL_DEPENDS}' -V '${DEPENDS}' \
	    -V '${BUILD_DEPENDS}' -V '${CROSS_TARGET_DEPENDS}'
}
clang=$(query clang) || fail "cannot query Clang fake-cross recipe"
clang_fc=$(printf '%s\n' "$clang" | sed -n '1p')
clang_tools=$(printf '%s\n' "$clang" | sed -n '2p')
clang_target=$(printf '%s\n' "$clang" | sed -n '5p')
[ "$clang_fc" = flang ] || fail "Clang target family selects $clang_fc instead of native Flang"
case " $clang_tools " in *" flang-"*) ;; *) fail "Clang target family does not select native Flang: $clang_tools";; esac
case " $clang_target " in *" flang-rt>="*":../../lang/flang-rt "*) ;; *) fail "Clang misses target Flang-RT: $clang_target";; esac
gcc=$(query gcc) || fail "cannot query GCC fake-cross recipe"
gcc_fc=$(printf '%s\n' "$gcc" | sed -n '1p')
gcc_tools=$(printf '%s\n' "$gcc" | sed -n '2p')
gcc_depends=$(printf '%s\n' "$gcc" | sed -n '3,5p' | tr '\n' ' ')
case "$gcc_fc" in */gfortran) ;; *) fail "GCC target family selects $gcc_fc instead of target gfortran";; esac
[ -z "$gcc_tools" ] || fail "GCC unexpectedly depends on native Flang: $gcc_tools"
case " $gcc_depends " in *flang-rt*) fail "GCC unexpectedly depends on Flang-RT: $gcc_depends";; esac

echo "PASS: fake-cross Clang uses host Flang and target Flang-RT; GCC uses target gfortran without Flang dependencies"

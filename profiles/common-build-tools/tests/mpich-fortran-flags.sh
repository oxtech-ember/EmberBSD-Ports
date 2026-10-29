#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). MPICH passes -fallow-argument-mismatch
# only to GFortran. Flang rejects the option, so a Clang-profile f90 build
# must not receive it, while a GFortran build keeps it.
# BMAKE runs the Ports bmake; CROSS_MAKECONF selects the Clang cross profile.
set -eu
[ "$#" = 3 ] || { echo 'Usage: mpich-fortran-flags.sh EXPORTED_PKGSRC CROSS_MAKECONF NEW_OUTPUT' >&2; exit 2; }
pkgsrc=$1 makeconf=$2 out=$3
: "${BMAKE:?Set BMAKE to the Ports bmake command}"
[ ! -e "$out" ] || { echo "FAIL: $out exists" >&2; exit 2; }
mkdir -p "$out"
flag=-fallow-argument-mismatch
query() {
	(cd "$pkgsrc/parallel/mpi-ch" && MAKECONF=$makeconf $BMAKE "$@" \
	    show-vars VARNAMES='EMBERBSD_CROSS_COMPILER_FAMILY PKG_OPTIONS PKG_FC FFLAGS')
}
query > "$out/clang" 2> "$out/clang.err"
family=$(sed -n 1p "$out/clang")
[ "$family" = clang ] || { echo "FAIL: the profile family is '$family', not clang" >&2; exit 1; }
case " $(sed -n 2p "$out/clang") " in *' f90 '*) ;; *) echo 'FAIL: the f90 option is not selected' >&2; exit 1;; esac
case "$(sed -n 3p "$out/clang")" in */flang) ;; *) echo 'FAIL: the Clang profile does not select Flang' >&2; exit 1;; esac
case " $(sed -n 4p "$out/clang") " in *" $flag "*)
	echo "FAIL: Flang receives the GFortran option $flag" >&2; exit 1;; esac
# The same recipe with a GFortran compiler keeps the option.
query PKG_FC=/fixture/bin/aarch64--netbsd-gfortran > "$out/gfortran" 2> "$out/gfortran.err"
case " $(sed -n 4p "$out/gfortran") " in *" $flag "*) ;; *)
	echo "FAIL: GFortran lost $flag" >&2; exit 1;; esac
echo 'PASS: MPICH passes -fallow-argument-mismatch to GFortran only'

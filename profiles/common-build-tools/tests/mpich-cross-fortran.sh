#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Check that a cross build of parallel/mpi-ch gives configure every
# CROSS_F77_* and CROSS_F90_* value that MPICH lists in
# maint/fcrosscompile/cross_values.txt.in. Without them configure stopped
# with "could not determine the size of a Fortran INTEGER".
#
# Usage: BMAKE=bmake mpich-cross-fortran.sh PKGSRC MAKECONF
# MAKECONF is the mk.conf of a NetBSD aarch64 cross build.

set -eu
[ $# -eq 2 ] || { echo "usage: BMAKE=bmake $0 PKGSRC MAKECONF" >&2; exit 2; }
pkgsrc=$1
makeconf=$2
bmake=${BMAKE:-bmake}

env_of() {
	MAKECONF=$makeconf "$bmake" -C "$pkgsrc/parallel/mpi-ch" \
	    MAKECONF="$makeconf" PKG_OPTIONS.mpich=f90 "$@" \
	    -V '${CONFIGURE_ENV:MCROSS_F*}'
}

cross=" $(env_of) "
for want in CROSS_F77_SIZEOF_INTEGER=4 CROSS_F77_SIZEOF_REAL=4 \
    CROSS_F77_SIZEOF_DOUBLE_PRECISION=8 CROSS_F77_TRUE_VALUE=1 \
    CROSS_F77_FALSE_VALUE=0 CROSS_F90_ADDRESS_KIND=8 \
    CROSS_F90_OFFSET_KIND=8 CROSS_F90_INTEGER_KIND=4 \
    CROSS_F90_REAL_MODEL=6,37 CROSS_F90_DOUBLE_MODEL=15,307 \
    CROSS_F90_INTEGER_MODEL=9 CROSS_F90_ALL_INTEGER_MODELS=2,1,4,2,9,4,18,8, \
    'CROSS_F90_INTEGER_MODEL_MAP=\{2,1,1\},\{4,2,2\},\{9,4,4\},\{18,8,8\},'; do
	case $cross in
	*" $want "*) ;;
	*) echo "FAIL: the aarch64 cross build lacks $want"; exit 1 ;;
	esac
done
native=$(env_of USE_CROSS_COMPILE=no)
if [ -n "$native" ]; then
	echo "FAIL: the native build should measure the values ('$native')"
	exit 1
fi
echo "PASS: the cross build gives MPICH all Fortran cross values"

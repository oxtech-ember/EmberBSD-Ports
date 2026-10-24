# SPDX-License-Identifier: BSD-2-Clause
BUILDLINK_TREE+= gcc16-fortran-runtime
.if !defined(GCC16_FORTRAN_RUNTIME_BUILDLINK3_MK)
GCC16_FORTRAN_RUNTIME_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.gcc16-fortran-runtime+= gcc16-fortran-runtime-16.2.0nb1
BUILDLINK_PKGSRCDIR.gcc16-fortran-runtime?= ../../lang/gcc16-fortran-runtime
BUILDLINK_LIBDIRS.gcc16-fortran-runtime= gcc16/lib
.endif
BUILDLINK_TREE+= -gcc16-fortran-runtime

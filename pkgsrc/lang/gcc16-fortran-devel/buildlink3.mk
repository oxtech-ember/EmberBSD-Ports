# SPDX-License-Identifier: BSD-2-Clause
BUILDLINK_TREE+= gcc16-fortran-devel
.if !defined(GCC16_FORTRAN_DEVEL_BUILDLINK3_MK)
GCC16_FORTRAN_DEVEL_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.gcc16-fortran-devel+= gcc16-fortran-devel=16.2.0
BUILDLINK_PKGSRCDIR.gcc16-fortran-devel?= ../../lang/gcc16-fortran-devel
BUILDLINK_DEPMETHOD.gcc16-fortran-devel?= build
BUILDLINK_LIBDIRS.gcc16-fortran-devel= gcc16/lib
BUILDLINK_INCDIRS.gcc16-fortran-devel= gcc16/lib/gcc/${MACHINE_GNU_PLATFORM}/16.2.0/include
.include "../../lang/gcc16-fortran-runtime/buildlink3.mk"
.endif
BUILDLINK_TREE+= -gcc16-fortran-devel

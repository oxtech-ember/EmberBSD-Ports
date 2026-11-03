# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
BUILDLINK_TREE+= libunwind-devel
.if !defined(LIBUNWINDDEVEL_BUILDLINK3_MK)
LIBUNWINDDEVEL_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.libunwind-devel+= libunwind-devel>=23.1.4nb3
BUILDLINK_PKGSRCDIR.libunwind-devel?= ../../lang/libunwind-devel
BUILDLINK_INCDIRS.libunwind-devel+= llvm/include/c++/v1 llvm/include
BUILDLINK_LIBDIRS.libunwind-devel+= llvm/lib
BUILDLINK_DEPMETHOD.libunwind-devel= build
.endif
BUILDLINK_TREE+= -libunwind-devel

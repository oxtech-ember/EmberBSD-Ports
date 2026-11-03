# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
BUILDLINK_TREE+= libcxx-devel
.if !defined(LIBCXXDEVEL_BUILDLINK3_MK)
LIBCXXDEVEL_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.libcxx-devel+= libcxx-devel>=23.1.4nb3
BUILDLINK_PKGSRCDIR.libcxx-devel?= ../../lang/libcxx-devel
BUILDLINK_INCDIRS.libcxx-devel+= llvm/include/c++/v1 llvm/include
BUILDLINK_LIBDIRS.libcxx-devel+= llvm/lib
BUILDLINK_DEPMETHOD.libcxx-devel= build
.endif
BUILDLINK_TREE+= -libcxx-devel

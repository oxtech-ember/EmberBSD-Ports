# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
BUILDLINK_TREE+= libcxxabi-devel
.if !defined(LIBCXXABIDEVEL_BUILDLINK3_MK)
LIBCXXABIDEVEL_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.libcxxabi-devel+= libcxxabi-devel>=23.1.4nb3
BUILDLINK_PKGSRCDIR.libcxxabi-devel?= ../../lang/libcxxabi-devel
BUILDLINK_INCDIRS.libcxxabi-devel+= llvm/include/c++/v1 llvm/include
BUILDLINK_LIBDIRS.libcxxabi-devel+= llvm/lib
BUILDLINK_DEPMETHOD.libcxxabi-devel= build
.endif
BUILDLINK_TREE+= -libcxxabi-devel

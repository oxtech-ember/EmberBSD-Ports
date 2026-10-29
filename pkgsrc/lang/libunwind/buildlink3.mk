# SPDX-License-Identifier: BSD-2-Clause
.include "../../mk/bsd.prefs.mk"
BUILDLINK_TREE+= libunwind
.if !defined(LIBUNWIND_BUILDLINK3_MK)
LIBUNWIND_BUILDLINK3_MK:=
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD" && !empty(EMBER_LLVM_CXX_STAGE:U)
BUILDLINK_API_DEPENDS.libunwind+= libunwind-devel>=23.1.4nb1
BUILDLINK_PKGSRCDIR.libunwind?= ../../lang/libunwind-devel
BUILDLINK_INCDIRS.libunwind+= llvm/include/c++/v1 llvm/include
BUILDLINK_LIBDIRS.libunwind+= llvm/lib
.else
BUILDLINK_API_DEPENDS.libunwind+= libunwind>=21.1.0
BUILDLINK_PKGSRCDIR.libunwind?= ../../lang/libunwind
.endif
.endif
BUILDLINK_TREE+= -libunwind

# SPDX-License-Identifier: BSD-2-Clause
.include "../../mk/bsd.prefs.mk"
BUILDLINK_TREE+= libunwind
.if !defined(LIBUNWIND_BUILDLINK3_MK)
LIBUNWIND_BUILDLINK3_MK:=
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD" && (!empty(EMBER_LLVM_CXX_STAGE:U) || !empty(EMBER_LLVM_CXX_SYSROOT:U))
BUILDLINK_API_DEPENDS.libunwind+= libunwind>=23.1.4nb3
BUILDLINK_PKGSRCDIR.libunwind?= ../../lang/libunwind
BUILDLINK_LIBDIRS.libunwind+= llvm/lib
.include "../../lang/libunwind-devel/buildlink3.mk"
.else
BUILDLINK_API_DEPENDS.libunwind+= libunwind>=21.1.0
BUILDLINK_PKGSRCDIR.libunwind?= ../../lang/libunwind
.endif
.endif
BUILDLINK_TREE+= -libunwind

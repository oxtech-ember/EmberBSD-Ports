# SPDX-License-Identifier: BSD-2-Clause
.include "../../mk/bsd.prefs.mk"
BUILDLINK_TREE+= libcxxabi
.if !defined(LIBCXXABI_BUILDLINK3_MK)
LIBCXXABI_BUILDLINK3_MK:=
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD" && (!empty(EMBER_LLVM_CXX_STAGE:U) || !empty(EMBER_LLVM_CXX_SYSROOT:U))
BUILDLINK_API_DEPENDS.libcxxabi+= libcxxabi>=23.1.4nb3
BUILDLINK_PKGSRCDIR.libcxxabi?= ../../lang/libcxxabi
BUILDLINK_LIBDIRS.libcxxabi+= llvm/lib
.include "../../lang/libcxxabi-devel/buildlink3.mk"
.else
BUILDLINK_API_DEPENDS.libcxxabi+= libcxxabi>=21.1.0
BUILDLINK_PKGSRCDIR.libcxxabi?= ../../lang/libcxxabi
.endif
.endif
BUILDLINK_TREE+= -libcxxabi

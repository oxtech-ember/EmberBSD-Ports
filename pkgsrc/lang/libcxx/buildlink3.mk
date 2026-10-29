# $NetBSD: buildlink3.mk,v 1.15 2026/04/16 06:33:51 wiz Exp $
.include "../../mk/bsd.prefs.mk"
BUILDLINK_TREE+= libcxx
.if !defined(LIBCXX_BUILDLINK3_MK)
LIBCXX_BUILDLINK3_MK:=
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD" && (!empty(EMBER_LLVM_CXX_STAGE:U) || !empty(EMBER_LLVM_CXX_SYSROOT:U))
BUILDLINK_API_DEPENDS.libcxx+= libcxx-devel>=23.1.4nb1
BUILDLINK_PKGSRCDIR.libcxx?= ../../lang/libcxx-devel
BUILDLINK_INCDIRS.libcxx+= llvm/include/c++/v1 llvm/include
BUILDLINK_LIBDIRS.libcxx+= llvm/lib
.else
BUILDLINK_API_DEPENDS.libcxx+= libcxx>=23.1.4
BUILDLINK_INCDIRS.libcxx+= include/libc++/v1
BUILDLINK_LIBDIRS.libcxx+= lib/libc++
BUILDLINK_PKGSRCDIR.libcxx?= ../../lang/libcxx
.endif
.endif
BUILDLINK_TREE+= -libcxx

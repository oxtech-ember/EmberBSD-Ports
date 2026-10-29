# $NetBSD: buildlink3.mk,v 1.6 2026/09/02 14:11:41 adam Exp $

BUILDLINK_TREE+=	spirv-llvm-translator

.if !defined(SPIRV_LLVM_TRANSLATOR_BUILDLINK3_MK)
SPIRV_LLVM_TRANSLATOR_BUILDLINK3_MK:=


BUILDLINK_API_DEPENDS.spirv-llvm-translator+=	spirv-llvm-translator>=23.1.2<23.2
BUILDLINK_ABI_DEPENDS.spirv-llvm-translator+=	spirv-llvm-translator>=23.1.2<23.2
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && \
    ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
BUILDLINK_ABI_DEPENDS.spirv-llvm-translator+= spirv-llvm-translator>=23.1.2nb1<23.2
.endif
BUILDLINK_PKGSRCDIR.spirv-llvm-translator?=	../../parallel/spirv-llvm-translator

.include "../../lang/llvm/buildlink3.mk"

BUILDLINK_FILES.spirv-llvm-translator+=	bin/llvm-spirv

.endif	# SPIRV_LLVM_TRANSLATOR_BUILDLINK3_MK

BUILDLINK_TREE+=	-spirv-llvm-translator

# $NetBSD: buildlink3.mk,v 1.5 2026/07/04 06:08:37 wiz Exp $

BUILDLINK_TREE+=	spirv-tools

.if !defined(SPIRV_TOOLS_BUILDLINK3_MK)
SPIRV_TOOLS_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.spirv-tools+=	spirv-tools>=2026.4nb1
BUILDLINK_ABI_DEPENDS.spirv-tools+=	spirv-tools>=2026.4nb1
.include "../../mk/bsd.fast.prefs.mk"
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && \
    ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
BUILDLINK_ABI_DEPENDS.spirv-tools+=	spirv-tools>=2026.4nb2
.endif
BUILDLINK_PKGSRCDIR.spirv-tools?=	../../parallel/spirv-tools
BUILDLINK_FILES.spirv-tools+=					\
					bin/spirv-as		\
					bin/spirv-cfg		\
					bin/spirv-diff		\
					bin/spirv-dis		\
					bin/spirv-link		\
					bin/spirv-lint		\
					bin/spirv-objdump	\
					bin/spirv-opt		\
					bin/spirv-reduce	\
					bin/spirv-val

.endif	# SPIRV_TOOLS_BUILDLINK3_MK

BUILDLINK_TREE+=	-spirv-tools

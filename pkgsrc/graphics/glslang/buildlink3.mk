# $NetBSD: buildlink3.mk,v 1.1 2026/04/13 14:38:43 kikadf Exp $

BUILDLINK_TREE+=	glslang

.if !defined(GLSLANG_BUILDLINK3_MK)
GLSLANG_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.glslang+=	glslang>=16.6.0
BUILDLINK_ABI_DEPENDS.glslang+=	glslang>=16.6.0nb1
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && \
    ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
BUILDLINK_ABI_DEPENDS.glslang+=	glslang>=16.6.0nb2
.endif
BUILDLINK_PKGSRCDIR.glslang?=	../../graphics/glslang

.endif	# GLSLANG_BUILDLINK3_MK

BUILDLINK_TREE+=	-glslang

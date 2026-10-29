# $NetBSD: buildlink3.mk,v 1.12 2026/04/16 06:33:49 wiz Exp $

BUILDLINK_TREE+=	lld

.if !defined(LLD_BUILDLINK3_MK)
LLD_BUILDLINK3_MK:=

.include "../../mk/bsd.fast.prefs.mk"
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && \
    ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
BUILDLINK_ABI_DEPENDS.lld+= lld>=23.1.4nb7
.endif

BUILDLINK_API_DEPENDS.lld+=	lld>=23.1.4
BUILDLINK_PKGSRCDIR.lld?=	../../devel/lld

.include "../../lang/llvm/buildlink3.mk"
.endif	# LLD_BUILDLINK3_MK

BUILDLINK_TREE+=	-lld

# $NetBSD: buildlink3.mk,v 1.58 2026/01/07 08:45:46 wiz Exp $

BUILDLINK_TREE+=	icu

.if !defined(ICU_BUILDLINK3_MK)
ICU_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.icu+=	icu>=3.4
BUILDLINK_ABI_DEPENDS.icu+=	icu>=79.1
BUILDLINK_PKGSRCDIR.icu?=	../../textproc/icu

.include "../../mk/bsd.fast.prefs.mk"
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
BUILDLINK_ABI_DEPENDS.icu+= icu>=79.1nb1
.endif
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD"
BUILDLINK_ABI_DEPENDS.icu+= icu>=79.1nb1
.include "../../textproc/icu-devel/buildlink3.mk"
.endif
.endif # ICU_BUILDLINK3_MK

BUILDLINK_TREE+=	-icu

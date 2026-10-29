# $NetBSD: buildlink3.mk,v 1.3 2026/07/06 17:27:14 adam Exp $

BUILDLINK_TREE+=	libjpeg-turbo

.if !defined(LIBJPEG_TURBO_BUILDLINK3_MK)
LIBJPEG_TURBO_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.libjpeg-turbo+=	libjpeg-turbo>=3.2.1
BUILDLINK_PKGSRCDIR.libjpeg-turbo?=	../../graphics/libjpeg-turbo

.include "../../graphics/libspng/buildlink3.mk"
.include "../../devel/zlib/buildlink3.mk"
.endif	# LIBJPEG_TURBO_BUILDLINK3_MK

BUILDLINK_TREE+=	-libjpeg-turbo

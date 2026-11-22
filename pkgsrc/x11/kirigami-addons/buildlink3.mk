# $NetBSD: buildlink3.mk,v 1.2 2025/12/21 20:17:06 markd Exp $

BUILDLINK_TREE+=	kirigami-addons

.if !defined(KIRIGAMI_ADDONS_BUILDLINK3_MK)
KIRIGAMI_ADDONS_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.kirigami-addons+=	kirigami-addons>=1.12.0
BUILDLINK_PKGSRCDIR.kirigami-addons?=	../../x11/kirigami-addons

.include "../../devel/kf6-kconfig/buildlink3.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.endif	# KIRIGAMI_ADDONS_BUILDLINK3_MK

BUILDLINK_TREE+=	-kirigami-addons

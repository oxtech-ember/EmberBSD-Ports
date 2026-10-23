# $NetBSD: buildlink3.mk,v 1.7 2026/09/02 19:05:23 wiz Exp $

BUILDLINK_TREE+=	plasma6-libplasma

.if !defined(PLASMA6_LIBPLASMA_BUILDLINK3_MK)
PLASMA6_LIBPLASMA_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.plasma6-libplasma+=	plasma6-libplasma>=6.8.0
BUILDLINK_ABI_DEPENDS.plasma6-libplasma?=		plasma6-libplasma>=6.8.0nb2
BUILDLINK_PKGSRCDIR.plasma6-libplasma?=		../../x11/plasma6-libplasma
# Cross KDE builds name these files relative to the buildlink prefix.
BUILDLINK_FILES.plasma6-libplasma+=	qt6/metatypes/qt6plasma_metatypes.json
BUILDLINK_FILES.plasma6-libplasma+=	qt6/metatypes/qt6plasmaquick_metatypes.json

.include "../../devel/kf6-kconfig/buildlink3.mk"
.include "../../devel/kf6-kcoreaddons/buildlink3.mk"
.include "../../devel/kf6-ki18n/buildlink3.mk"
.include "../../devel/kf6-kio/buildlink3.mk"
.include "../../devel/kf6-knotifications/buildlink3.mk"
.include "../../devel/kf6-kpackage/buildlink3.mk"
.include "../../graphics/kf6-kiconthemes/buildlink3.mk"
.include "../../graphics/kf6-ksvg/buildlink3.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../x11/kf6-kglobalaccel/buildlink3.mk"
.include "../../x11/kf6-kguiaddons/buildlink3.mk"
.include "../../x11/kf6-kirigami/buildlink3.mk"
.include "../../x11/kf6-kwindowsystem/buildlink3.mk"
.include "../../x11/plasma6-plasma-activities/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.endif	# PLASMA6_LIBPLASMA_BUILDLINK3_MK

BUILDLINK_TREE+=	-plasma6-libplasma

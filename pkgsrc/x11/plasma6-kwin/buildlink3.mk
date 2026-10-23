# $NetBSD$

BUILDLINK_TREE+=	plasma6-kwin

.if !defined(PLASMA6_KWIN_BUILDLINK3_MK)
PLASMA6_KWIN_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.plasma6-kwin+=	plasma6-kwin>=6.8.0
BUILDLINK_PKGSRCDIR.plasma6-kwin?=	../../x11/plasma6-kwin
# The KWin CMake package and headers are not under a versioned include dir.
BUILDLINK_FILES.plasma6-kwin+=	include/kwin/*
BUILDLINK_FILES.plasma6-kwin+=	include/kwin/*/*
BUILDLINK_FILES.plasma6-kwin+=	lib/cmake/KWin/*

.include "../../devel/kf6-kconfig/buildlink3.mk"
.include "../../devel/kf6-kcoreaddons/buildlink3.mk"
.include "../../x11/kf6-kwindowsystem/buildlink3.mk"
.include "../../devel/wayland/buildlink3.mk"
.include "../../graphics/MesaLib/buildlink3.mk"
.include "../../graphics/libepoxy/buildlink3.mk"
.include "../../graphics/lcms2/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.endif # PLASMA6_KWIN_BUILDLINK3_MK

BUILDLINK_TREE+=	-plasma6-kwin

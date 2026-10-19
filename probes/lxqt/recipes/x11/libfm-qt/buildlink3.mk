# $NetBSD: buildlink3.mk,v 1.44 2026/09/02 19:05:16 wiz Exp $

BUILDLINK_TREE+=	libfm-qt

.if !defined(LIBFM_QT_BUILDLINK3_MK)
LIBFM_QT_BUILDLINK3_MK:=

# CMake consumers need the relocatable public dependency target export.
BUILDLINK_API_DEPENDS.libfm-qt+=	libfm-qt>=2.4.0nb5
# The shared library keeps its existing SONAME and exported ABI.
BUILDLINK_ABI_DEPENDS.libfm-qt?=	libfm-qt>=2.4.0nb2
BUILDLINK_PKGSRCDIR.libfm-qt?=		../../x11/libfm-qt

USE_TOOLS+=	pkg-config

.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../graphics/libexif/buildlink3.mk"
.include "../../sysutils/menu-cache/buildlink3.mk"
.endif	# LIBFM_QT_BUILDLINK3_MK

BUILDLINK_TREE+=	-libfm-qt

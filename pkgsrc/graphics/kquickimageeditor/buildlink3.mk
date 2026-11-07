# $NetBSD: buildlink3.mk,v 1.1 2026/11/07 00:00:00 emberbsd Exp $

BUILDLINK_TREE+=	kquickimageeditor

.if !defined(KQUICKIMAGEEDITOR_BUILDLINK3_MK)
KQUICKIMAGEEDITOR_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.kquickimageeditor+=	kquickimageeditor>=0.7
BUILDLINK_PKGSRCDIR.kquickimageeditor?=		../../graphics/kquickimageeditor

.include "../../devel/highway/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.endif

BUILDLINK_TREE+=	-kquickimageeditor

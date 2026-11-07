# $NetBSD: buildlink3.mk,v 1.1 2026/11/07 00:00:00 emberbsd Exp $

BUILDLINK_TREE+=	plasma6-kpipewire

.if !defined(PLASMA6_KPIPEWIRE_BUILDLINK3_MK)
PLASMA6_KPIPEWIRE_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.plasma6-kpipewire+=	plasma6-kpipewire>=6.8.2
BUILDLINK_PKGSRCDIR.plasma6-kpipewire?=		../../multimedia/plasma6-kpipewire

.include "../../multimedia/pipewire/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.endif

BUILDLINK_TREE+=	-plasma6-kpipewire

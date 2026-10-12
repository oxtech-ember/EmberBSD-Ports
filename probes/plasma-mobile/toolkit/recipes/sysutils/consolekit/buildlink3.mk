# $NetBSD: buildlink3.mk,v 1.15 2026/09/02 19:04:25 wiz Exp $

BUILDLINK_TREE+=	consolekit

.if !defined(CONSOLEKIT_BUILDLINK3_MK)
CONSOLEKIT_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.consolekit+=	consolekit>=2.0.0
BUILDLINK_ABI_DEPENDS.consolekit+=	consolekit>=2.0.0
BUILDLINK_PKGSRCDIR.consolekit?=	../../sysutils/consolekit

.include "../../sysutils/dbus/buildlink3.mk"
.include "../../devel/glib2/buildlink3.mk"
.endif # CONSOLEKIT_BUILDLINK3_MK

BUILDLINK_TREE+=	-consolekit

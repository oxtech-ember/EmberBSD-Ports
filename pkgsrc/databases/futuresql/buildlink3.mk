# $NetBSD$

BUILDLINK_TREE+=	futuresql

.if !defined(FUTURESQL_BUILDLINK3_MK)
FUTURESQL_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.futuresql+=	futuresql>=0.1.0
BUILDLINK_PKGSRCDIR.futuresql?=		../../databases/futuresql

.include "../../x11/qt6-qtbase/buildlink3.mk"
.endif	# FUTURESQL_BUILDLINK3_MK

BUILDLINK_TREE+=	-futuresql

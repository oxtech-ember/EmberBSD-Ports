# $NetBSD: buildlink3.mk,v 1.1 2020/03/31 10:43:54 nia Exp $

BUILDLINK_TREE+=	range-v3

.if !defined(RANGE_V3_BUILDLINK3_MK)
RANGE_V3_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.range-v3+=	range-v3>=0.12.0
BUILDLINK_PKGSRCDIR.range-v3?=		../../devel/range-v3
# Only installs libraries.
BUILDLINK_DEPMETHOD.range-v3?=		build
.endif	# RANGE_V3_BUILDLINK3_MK

BUILDLINK_TREE+=	-range-v3

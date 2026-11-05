# $NetBSD$

BUILDLINK_TREE+=	toomanycooks

.if !defined(TOOMANYCOOKS_BUILDLINK3_MK)
TOOMANYCOOKS_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.toomanycooks+=	toomanycooks>=1.6.1
BUILDLINK_PKGSRCDIR.toomanycooks?=	../../devel/toomanycooks
.include "../../parallel/hwloc/buildlink3.mk"
.endif

BUILDLINK_TREE+=	-toomanycooks

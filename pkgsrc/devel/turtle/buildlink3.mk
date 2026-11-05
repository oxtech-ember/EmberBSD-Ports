# $NetBSD$
BUILDLINK_TREE+=	turtle
.if !defined(TURTLE_BUILDLINK3_MK)
TURTLE_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.turtle+=	turtle>=2.0.0
BUILDLINK_ABI_DEPENDS.turtle?=	turtle>=2.0.0
BUILDLINK_PKGSRCDIR.turtle?=	../../devel/turtle
BUILDLINK_DEPMETHOD.turtle?=	build
.include "../../devel/boost-headers/buildlink3.mk"
.endif
BUILDLINK_TREE+=	-turtle

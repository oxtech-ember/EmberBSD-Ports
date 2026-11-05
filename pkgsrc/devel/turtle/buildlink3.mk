# $NetBSD$
BUILDLINK_TREE+=\tturtle
.if !defined(TURTLE_BUILDLINK3_MK)
TURTLE_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.turtle+=\tturtle>=2.0.0
BUILDLINK_ABI_DEPENDS.turtle?=\tturtle>=2.0.0
BUILDLINK_PKGSRCDIR.turtle?=\t../../devel/turtle
BUILDLINK_DEPMETHOD.turtle?=\tbuild
.include "../../devel/boost-headers/buildlink3.mk"
.endif
BUILDLINK_TREE+=\t-turtle

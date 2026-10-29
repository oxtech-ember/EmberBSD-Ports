# $NetBSD$
BUILDLINK_TREE+= meshoptimizer
.if !defined(MESHOPTIMIZER_BUILDLINK3_MK)
MESHOPTIMIZER_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.meshoptimizer+= meshoptimizer>=1.3
BUILDLINK_PKGSRCDIR.meshoptimizer?= ../../graphics/meshoptimizer
.endif
BUILDLINK_TREE+= -meshoptimizer

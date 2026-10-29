# $NetBSD$
BUILDLINK_TREE+= embree
.if !defined(EMBREE_BUILDLINK3_MK)
EMBREE_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.embree+= embree>=4.4.1
BUILDLINK_PKGSRCDIR.embree?= ../../graphics/embree
.include "../../parallel/threadingbuildingblocks/buildlink3.mk"
.endif
BUILDLINK_TREE+= -embree

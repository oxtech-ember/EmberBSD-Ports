# $NetBSD$
BUILDLINK_TREE+= nbytes
.if !defined(NBYTES_BUILDLINK3_MK)
NBYTES_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.nbytes+= nbytes>=0.1.4
BUILDLINK_PKGSRCDIR.nbytes?= ../../devel/nbytes
.endif
BUILDLINK_TREE+= -nbytes

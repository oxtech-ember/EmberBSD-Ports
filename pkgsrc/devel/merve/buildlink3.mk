# $NetBSD$
BUILDLINK_TREE+= merve
.if !defined(MERVE_BUILDLINK3_MK)
MERVE_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.merve+= merve>=1.2.2
BUILDLINK_PKGSRCDIR.merve?= ../../devel/merve
.endif
BUILDLINK_TREE+= -merve

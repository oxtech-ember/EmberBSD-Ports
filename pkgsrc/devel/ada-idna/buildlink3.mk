# $NetBSD$
BUILDLINK_TREE+= ada-idna
.if !defined(ADA_IDNA_BUILDLINK3_MK)
ADA_IDNA_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.ada-idna+= ada-idna>=0.7.0
BUILDLINK_PKGSRCDIR.ada-idna?= ../../devel/ada-idna
.endif
BUILDLINK_TREE+= -ada-idna

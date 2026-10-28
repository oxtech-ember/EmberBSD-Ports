# $NetBSD$
BUILDLINK_TREE+= ada-url
.if !defined(ADA_URL_BUILDLINK3_MK)
ADA_URL_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.ada-url+= ada-url>=4.0.0
BUILDLINK_PKGSRCDIR.ada-url?= ../../devel/ada-url
.include "../../devel/ada-idna/buildlink3.mk"
.endif
BUILDLINK_TREE+= -ada-url

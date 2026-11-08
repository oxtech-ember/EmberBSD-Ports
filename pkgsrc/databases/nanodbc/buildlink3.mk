# $NetBSD$
BUILDLINK_TREE+= nanodbc
.if !defined(NANODBC_BUILDLINK3_MK)
NANODBC_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.nanodbc+= nanodbc>=3.0.8
BUILDLINK_PKGSRCDIR.nanodbc?= ../../databases/nanodbc
.include "../../databases/unixodbc/buildlink3.mk"
.include "../../devel/boost-libs/buildlink3.mk"
.endif
BUILDLINK_TREE+= -nanodbc

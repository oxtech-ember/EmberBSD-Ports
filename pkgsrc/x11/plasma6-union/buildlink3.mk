# $NetBSD$

BUILDLINK_TREE+=	plasma6-union

.if !defined(PLASMA6_UNION_BUILDLINK3_MK)
PLASMA6_UNION_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.plasma6-union+=	plasma6-union>=6.8.2
BUILDLINK_PKGSRCDIR.plasma6-union?=	../../x11/plasma6-union

.include "../../archivers/kf6-karchive/buildlink3.mk"
.include "../../devel/cxx-rust-cssparser/buildlink3.mk"
.include "../../devel/ryml/buildlink3.mk"
.endif # PLASMA6_UNION_BUILDLINK3_MK

BUILDLINK_TREE+=	-plasma6-union

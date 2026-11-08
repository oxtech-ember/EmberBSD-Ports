# $NetBSD$
BUILDLINK_TREE+=	nanosvg

.if !defined(NANOSVG_BUILDLINK3_MK)
NANOSVG_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.nanosvg+=	nanosvg>=20261029
BUILDLINK_PKGSRCDIR.nanosvg?=	../../graphics/nanosvg
.endif

BUILDLINK_TREE+=	-nanosvg

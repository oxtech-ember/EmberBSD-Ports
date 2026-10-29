# $NetBSD$
BUILDLINK_TREE+= miniz
.if !defined(MINIZ_BUILDLINK3_MK)
MINIZ_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.miniz+= miniz>=3.1.2
BUILDLINK_PKGSRCDIR.miniz?= ../../archivers/miniz
.endif
BUILDLINK_TREE+= -miniz

# $NetBSD$

BUILDLINK_TREE+=	nanoflann

.if !defined(NANOFLANN_BUILDLINK3_MK)
NANOFLANN_BUILDLINK3_MK:=

BUILDLINK_FILES.nanoflann+=	share/cmake/nanoflann/*.cmake
BUILDLINK_FILES.nanoflann+=	lib/pkgconfig/nanoflann.pc

BUILDLINK_DEPMETHOD.nanoflann?=	build
BUILDLINK_API_DEPENDS.nanoflann+=	nanoflann>=2.0.1
BUILDLINK_PKGSRCDIR.nanoflann?=	../../math/nanoflann

.endif # NANOFLANN_BUILDLINK3_MK

BUILDLINK_TREE+=	-nanoflann

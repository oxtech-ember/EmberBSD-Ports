# $NetBSD$

BUILDLINK_TREE+=	rapidcsv

.if !defined(RAPIDCSV_BUILDLINK3_MK)
RAPIDCSV_BUILDLINK3_MK:=

BUILDLINK_FILES.rapidcsv+=	lib/cmake/rapidcsv/*.cmake

BUILDLINK_DEPMETHOD.rapidcsv?=	build
BUILDLINK_API_DEPENDS.rapidcsv+=	rapidcsv>=9.07
BUILDLINK_PKGSRCDIR.rapidcsv?=	../../textproc/rapidcsv

.endif # RAPIDCSV_BUILDLINK3_MK

BUILDLINK_TREE+=	-rapidcsv

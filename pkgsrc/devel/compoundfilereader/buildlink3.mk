# $NetBSD$

BUILDLINK_TREE+=	compoundfilereader

.if !defined(COMPOUNDFILEREADER_BUILDLINK3_MK)
COMPOUNDFILEREADER_BUILDLINK3_MK:=

BUILDLINK_FILES.compoundfilereader+=	lib/cmake/CompoundFileReader/*.cmake
BUILDLINK_DEPMETHOD.compoundfilereader?=	build
BUILDLINK_API_DEPENDS.compoundfilereader+=	compoundfilereader>=0.0.20250414
BUILDLINK_PKGSRCDIR.compoundfilereader?=	../../devel/compoundfilereader

.endif # COMPOUNDFILEREADER_BUILDLINK3_MK

BUILDLINK_TREE+=	-compoundfilereader

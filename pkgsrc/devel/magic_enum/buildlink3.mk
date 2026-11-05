# $NetBSD$

BUILDLINK_TREE+=	magic_enum

.if !defined(MAGIC_ENUM_BUILDLINK3_MK)
MAGIC_ENUM_BUILDLINK3_MK:=

BUILDLINK_FILES.magic_enum+=	share/cmake/magic_enum/*.cmake
BUILDLINK_FILES.magic_enum+=	share/pkgconfig/magic_enum.pc

BUILDLINK_DEPMETHOD.magic_enum?=	build
BUILDLINK_API_DEPENDS.magic_enum+=	magic_enum>=0.9.8
BUILDLINK_PKGSRCDIR.magic_enum?=	../../devel/magic_enum

.endif # MAGIC_ENUM_BUILDLINK3_MK

BUILDLINK_TREE+=	-magic_enum

# $NetBSD$

BUILDLINK_TREE+=	libpopcnt

.if !defined(LIBPOPCNT_BUILDLINK3_MK)
LIBPOPCNT_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.libpopcnt+=	libpopcnt>=4.2
BUILDLINK_PKGSRCDIR.libpopcnt?=	../../devel/libpopcnt
BUILDLINK_DEPMETHOD.libpopcnt?=	build
.endif

BUILDLINK_TREE+=	-libpopcnt

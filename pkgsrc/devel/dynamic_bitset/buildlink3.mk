# $NetBSD$

BUILDLINK_TREE+=	dynamic_bitset

.if !defined(DYNAMIC_BITSET_BUILDLINK3_MK)
DYNAMIC_BITSET_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.dynamic_bitset+=	dynamic_bitset>=1.3.3
BUILDLINK_PKGSRCDIR.dynamic_bitset?=	../../devel/dynamic_bitset
BUILDLINK_DEPMETHOD.dynamic_bitset?=	build
.include "../../devel/libpopcnt/buildlink3.mk"
.endif

BUILDLINK_TREE+=	-dynamic_bitset

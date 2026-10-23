# $NetBSD: buildlink3.mk,v 1.1 2026/04/13 15:24:45 kikadf Exp $

BUILDLINK_TREE+=	input-headers

.if !defined(INPUT_HEADERS_BUILDLINK3_MK)
INPUT_HEADERS_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.input-headers+=	input-headers>=1.31.3
BUILDLINK_ABI_DEPENDS.input-headers+=	input-headers>=1.31.3
BUILDLINK_PKGSRCDIR.input-headers?=	../../devel/input-headers

.endif # INPUT_HEADERS_BUILDLINK3_MK

BUILDLINK_TREE+=	-input-headers

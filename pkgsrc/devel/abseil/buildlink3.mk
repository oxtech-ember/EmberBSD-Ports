# $NetBSD: buildlink3.mk,v 1.14 2026/08/26 10:09:07 adam Exp $

BUILDLINK_TREE+=	abseil

.if !defined(ABSEIL_BUILDLINK3_MK)
ABSEIL_BUILDLINK3_MK:=

USE_CXX_FEATURES+=	c++17 filesystem

BUILDLINK_API_DEPENDS.abseil+=	abseil>=20220623.0
BUILDLINK_ABI_DEPENDS.abseil+=	abseil>=20260817.0nb3
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
BUILDLINK_ABI_DEPENDS.abseil+=	abseil>=20260817.0nb4
.endif
BUILDLINK_PKGSRCDIR.abseil?=	../../devel/abseil
.endif	# ABSEIL_BUILDLINK3_MK

BUILDLINK_TREE+=	-abseil

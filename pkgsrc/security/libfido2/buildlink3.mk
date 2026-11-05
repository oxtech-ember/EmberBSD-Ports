# $NetBSD: buildlink3.mk,v 1.6 2023/12/07 12:35:46 adam Exp $

BUILDLINK_TREE+=	libfido2

.if !defined(LIBFIDO2_BUILDLINK3_MK)
LIBFIDO2_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.libfido2+=	libfido2>=1.10.0
BUILDLINK_ABI_DEPENDS.libfido2+=	libfido2>=1.17.0nb2
BUILDLINK_PKGSRCDIR.libfido2?=		../../security/libfido2

USE_BUILTIN.openssl=	no
BUILDLINK_ABI_DEPENDS.openssl+=	openssl>=4
.include "../../devel/libcbor/buildlink3.mk"
.include "../../devel/zlib/buildlink3.mk"
.include "../../security/openssl/buildlink3.mk"
.endif	# LIBFIDO2_BUILDLINK3_MK

BUILDLINK_TREE+=	-libfido2

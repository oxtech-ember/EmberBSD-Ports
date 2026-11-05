BUILDLINK_TREE+= libsrtp
.if !defined(LIBSRTP_BUILDLINK3_MK)
LIBSRTP_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.libsrtp+= libsrtp>=2.8.1
BUILDLINK_PKGSRCDIR.libsrtp?= ../../security/libsrtp
.include "../../security/openssl/buildlink3.mk"
.endif
BUILDLINK_TREE+= -libsrtp

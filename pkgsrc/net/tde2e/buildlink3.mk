BUILDLINK_TREE+= tde2e
.if !defined(TDE2E_BUILDLINK3_MK)
TDE2E_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.tde2e+= tde2e>=1.8.69
BUILDLINK_PKGSRCDIR.tde2e?= ../../net/tde2e
.include "../../security/openssl/buildlink3.mk"
.include "../../devel/zlib/buildlink3.mk"
.endif
BUILDLINK_TREE+= -tde2e

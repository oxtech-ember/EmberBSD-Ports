# $NetBSD$

BUILDLINK_TREE+=	zint-lib

.if !defined(ZINT_LIB_BUILDLINK3_MK)
ZINT_LIB_BUILDLINK3_MK:=

.include "../../graphics/zint/version.mk"

BUILDLINK_API_DEPENDS.zint-lib+=	zint-lib>=${ZINT_VERSION}nb${ZINT_LIB_REVISION}
BUILDLINK_PKGSRCDIR.zint-lib?=	../../graphics/zint-lib
BUILDLINK_DEPMETHOD.zint-lib?=	full

.include "../../graphics/png/buildlink3.mk"
.endif	# ZINT_LIB_BUILDLINK3_MK

BUILDLINK_TREE+=	-zint-lib

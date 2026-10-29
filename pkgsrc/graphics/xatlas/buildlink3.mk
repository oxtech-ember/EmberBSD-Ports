# $NetBSD$
BUILDLINK_TREE+= xatlas
.if !defined(XATLAS_BUILDLINK3_MK)
XATLAS_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.xatlas+= xatlas>=20220725
BUILDLINK_PKGSRCDIR.xatlas?= ../../graphics/xatlas
PTHREAD_OPTS+= require
.include "../../mk/pthread.buildlink3.mk"
.endif
BUILDLINK_TREE+= -xatlas

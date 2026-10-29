# $NetBSD$
BUILDLINK_TREE+= nbytes
.if !defined(NBYTES_BUILDLINK3_MK)
NBYTES_BUILDLINK3_MK:=
.include "../../mk/bsd.fast.prefs.mk"
BUILDLINK_API_DEPENDS.nbytes+= nbytes>=0.1.4
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
BUILDLINK_ABI_DEPENDS.nbytes+= nbytes>=0.1.4nb2
.endif
BUILDLINK_PKGSRCDIR.nbytes?= ../../devel/nbytes
.endif
BUILDLINK_TREE+= -nbytes

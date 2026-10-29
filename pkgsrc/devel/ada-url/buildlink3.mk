# $NetBSD$
BUILDLINK_TREE+= ada-url
.if !defined(ADA_URL_BUILDLINK3_MK)
ADA_URL_BUILDLINK3_MK:=
.include "../../mk/bsd.fast.prefs.mk"
BUILDLINK_API_DEPENDS.ada-url+= ada-url>=4.0.0
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
BUILDLINK_ABI_DEPENDS.ada-url+= ada-url>=4.0.0nb1
.endif
BUILDLINK_PKGSRCDIR.ada-url?= ../../devel/ada-url
.include "../../devel/ada-idna/buildlink3.mk"
.endif
BUILDLINK_TREE+= -ada-url

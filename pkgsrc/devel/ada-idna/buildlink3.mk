# $NetBSD$
BUILDLINK_TREE+= ada-idna
.if !defined(ADA_IDNA_BUILDLINK3_MK)
ADA_IDNA_BUILDLINK3_MK:=
.include "../../mk/bsd.fast.prefs.mk"
BUILDLINK_API_DEPENDS.ada-idna+= ada-idna>=0.7.0
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
BUILDLINK_ABI_DEPENDS.ada-idna+= ada-idna>=0.7.0nb1
.endif
BUILDLINK_PKGSRCDIR.ada-idna?= ../../devel/ada-idna
.endif
BUILDLINK_TREE+= -ada-idna

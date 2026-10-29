# $NetBSD$
BUILDLINK_TREE+= merve
.if !defined(MERVE_BUILDLINK3_MK)
MERVE_BUILDLINK3_MK:=
.include "../../mk/bsd.fast.prefs.mk"
BUILDLINK_API_DEPENDS.merve+= merve>=1.2.2
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
BUILDLINK_ABI_DEPENDS.merve+= merve>=1.2.2nb1
.endif
BUILDLINK_PKGSRCDIR.merve?= ../../devel/merve
.endif
BUILDLINK_TREE+= -merve

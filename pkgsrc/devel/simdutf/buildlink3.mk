# $NetBSD$
BUILDLINK_TREE+= simdutf
.if !defined(SIMDUTF_BUILDLINK3_MK)
SIMDUTF_BUILDLINK3_MK:=
.include "../../mk/bsd.fast.prefs.mk"
BUILDLINK_API_DEPENDS.simdutf+= simdutf>=9.3.3
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
BUILDLINK_ABI_DEPENDS.simdutf+= simdutf>=9.3.3nb1
.endif
BUILDLINK_PKGSRCDIR.simdutf?= ../../devel/simdutf
.endif
BUILDLINK_TREE+= -simdutf

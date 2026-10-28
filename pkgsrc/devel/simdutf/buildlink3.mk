# $NetBSD$
BUILDLINK_TREE+= simdutf
.if !defined(SIMDUTF_BUILDLINK3_MK)
SIMDUTF_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.simdutf+= simdutf>=9.3.0
BUILDLINK_PKGSRCDIR.simdutf?= ../../devel/simdutf
.endif
BUILDLINK_TREE+= -simdutf

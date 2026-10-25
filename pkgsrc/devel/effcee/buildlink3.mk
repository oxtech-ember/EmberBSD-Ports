# $NetBSD$
BUILDLINK_TREE+= effcee
.if !defined(EFFCEE_BUILDLINK3_MK)
EFFCEE_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.effcee+= effcee>=1.2026.0nb1
BUILDLINK_PKGSRCDIR.effcee?= ../../devel/effcee
USE_CXX_FEATURES+= c++17
.include "../../devel/re2/buildlink3.mk"
.endif
BUILDLINK_TREE+= -effcee

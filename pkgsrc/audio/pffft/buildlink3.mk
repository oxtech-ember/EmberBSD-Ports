# $NetBSD$
BUILDLINK_TREE+= pffft
.if !defined(PFFFT_BUILDLINK3_MK)
PFFFT_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.pffft+= pffft>=1.1.0
BUILDLINK_PKGSRCDIR.pffft?= ../../audio/pffft
.endif
BUILDLINK_TREE+= -pffft

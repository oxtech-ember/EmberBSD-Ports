# $NetBSD$
BUILDLINK_TREE+= libtommath
.if !defined(LIBTOMMATH_BUILDLINK3_MK)
LIBTOMMATH_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.libtommath+= libtommath>=1.3.0
BUILDLINK_PKGSRCDIR.libtommath?= ../../math/libtommath
.endif
BUILDLINK_TREE+= -libtommath

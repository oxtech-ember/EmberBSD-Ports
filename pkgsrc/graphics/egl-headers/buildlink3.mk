# $NetBSD$
BUILDLINK_TREE+=	egl-headers

.if !defined(EGL_HEADERS_BUILDLINK3_MK)
EGL_HEADERS_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.egl-headers+=	egl-headers>=20261106
BUILDLINK_PKGSRCDIR.egl-headers?=	../../graphics/egl-headers

.endif # EGL_HEADERS_BUILDLINK3_MK
BUILDLINK_TREE+=	-egl-headers

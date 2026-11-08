# $NetBSD$
BUILDLINK_TREE+=	libcontext
.if !defined(LIBCONTEXT_BUILDLINK3_MK)
LIBCONTEXT_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.libcontext+=	libcontext>=20261029
BUILDLINK_PKGSRCDIR.libcontext?=	../../devel/libcontext
.endif
BUILDLINK_TREE+=	-libcontext

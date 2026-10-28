# $NetBSD$
BUILDLINK_TREE+= llhttp
.if !defined(LLHTTP_BUILDLINK3_MK)
LLHTTP_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.llhttp+= llhttp>=9.4.3
BUILDLINK_PKGSRCDIR.llhttp?= ../../www/llhttp
.endif
BUILDLINK_TREE+= -llhttp

# $NetBSD$

BUILDLINK_TREE+=	gzip-hpp

.if !defined(GZIP_HPP_BUILDLINK3_MK)
GZIP_HPP_BUILDLINK3_MK:=

BUILDLINK_FILES.gzip-hpp+=	lib/cmake/gzip-hpp/*.cmake
BUILDLINK_DEPMETHOD.gzip-hpp?=	build
BUILDLINK_API_DEPENDS.gzip-hpp+=	gzip-hpp>=0.1.0nb1
BUILDLINK_PKGSRCDIR.gzip-hpp?=	../../archivers/gzip-hpp

.include "../../devel/zlib/buildlink3.mk"
.endif # GZIP_HPP_BUILDLINK3_MK

BUILDLINK_TREE+=	-gzip-hpp

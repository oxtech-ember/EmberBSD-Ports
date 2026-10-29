# $NetBSD: buildlink3.mk,v 1.3 2025/06/08 07:46:04 wiz Exp $

BUILDLINK_TREE+=	assimp

.if !defined(ASSIMP_BUILDLINK3_MK)
ASSIMP_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.assimp+=	assimp>=6.0.5nb1
BUILDLINK_ABI_DEPENDS.assimp+=	assimp>=6.0.5nb1
BUILDLINK_PKGSRCDIR.assimp?=	../../multimedia/assimp

.include "../../devel/zlib/buildlink3.mk"
.include "../../archivers/minizip/buildlink3.mk"
.include "../../archivers/libzip/buildlink3.mk"
.include "../../textproc/pugixml/buildlink3.mk"
.include "../../math/poly2tri/buildlink3.mk"
.include "../../math/open3dgc/buildlink3.mk"
.include "../../math/clipper2/buildlink3.mk"
.include "../../devel/openddl-parser/buildlink3.mk"
.endif	# ASSIMP_BUILDLINK3_MK

BUILDLINK_TREE+=	-assimp

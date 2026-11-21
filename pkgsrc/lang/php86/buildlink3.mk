# $NetBSD: buildlink3.mk,v 1.1 2026/01/08 13:38:00 taca Exp $

BUILDLINK_TREE+=	php86

.if !defined(PHP86_BUILDLINK3_MK)
PHP86_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.php86+=	php86>=8.6.0<8.7
BUILDLINK_ABI_DEPENDS.php86+=	php86>=8.6.0
BUILDLINK_PKGSRCDIR.php86?=	../../lang/php86
BUILDLINK_INCDIRS.php86+=	${PHP_INCDIR}

pkgbase := php86
.include "../../mk/pkg-build-options.mk"
.include "../../textproc/libxml2/buildlink3.mk"
.endif # PHP86_BUILDLINK3_MK

BUILDLINK_TREE+=	-php86

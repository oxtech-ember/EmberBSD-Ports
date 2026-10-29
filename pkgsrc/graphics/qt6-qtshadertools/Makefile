# $NetBSD: Makefile,v 1.31 2026/09/02 19:02:54 wiz Exp $

DISTNAME=	qtshadertools-everywhere-src-${QTVERSION}
PKGNAME=	qt6-qtshadertools-${QTVERSION}
PKGREVISION=	2
COMMENT=	Qt6 shadertools
CATEGORIES=	graphics
LICENSE=	gnu-gpl-v3

.include "../../x11/qt6-qtbase/Makefile.common"

PKGCONFIG_OVERRIDE+=	lib/pkgconfig/Qt6ShaderTools.pc

.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../graphics/glslang/buildlink3.mk"
.include "../../graphics/spirv-cross/buildlink3.mk"
# Shader remapping links SPIRV-Tools statically and needs the fixed validator.
BUILDLINK_ABI_DEPENDS.spirv-tools+=	spirv-tools>=2026.4nb3
.include "../../parallel/spirv-tools/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

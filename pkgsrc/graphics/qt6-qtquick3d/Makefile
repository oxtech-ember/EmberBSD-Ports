# $NetBSD: Makefile,v 1.33 2026/09/02 19:02:53 wiz Exp $

DISTNAME=	qtquick3d-everywhere-src-${QTVERSION}
PKGNAME=	qt6-qtquick3d-${QTVERSION}
PKGREVISION=	4
COMMENT=	3d engine for Qt6 quick
CATEGORIES=	graphics
LICENSE=	gnu-gpl-v3

.include "../../x11/qt6-qtbase/Makefile.common"

PKGCONFIG_OVERRIDE+=	lib/pkgconfig/Qt6Quick3D.pc
PKGCONFIG_OVERRIDE+=	lib/pkgconfig/Qt6Quick3DAssetImport.pc
PKGCONFIG_OVERRIDE+=	lib/pkgconfig/Qt6Quick3DAssetUtils.pc
PKGCONFIG_OVERRIDE+=	lib/pkgconfig/Qt6Quick3DEffects.pc
PKGCONFIG_OVERRIDE+=	lib/pkgconfig/Qt6Quick3DHelpers.pc
PKGCONFIG_OVERRIDE+=	lib/pkgconfig/Qt6Quick3DHelpersImpl.pc
PKGCONFIG_OVERRIDE+=	lib/pkgconfig/Qt6Quick3DIblBaker.pc
PKGCONFIG_OVERRIDE+=	lib/pkgconfig/Qt6Quick3DParticleEffects.pc
PKGCONFIG_OVERRIDE+=	lib/pkgconfig/Qt6Quick3DParticles.pc
PKGCONFIG_OVERRIDE+=	lib/pkgconfig/Qt6Quick3DRuntimeRender.pc
PKGCONFIG_OVERRIDE+=	lib/pkgconfig/Qt6Quick3DUtils.pc

.if !empty(MACHINE_PLATFORM:MDarwin-*-aarch64) \
 || !empty(MACHINE_PLATFORM:MDarwin-*-x86_64) \
 || !empty(MACHINE_PLATFORM:MLinux-*-aarch64) \
 || !empty(MACHINE_PLATFORM:MLinux-*-x86_64)
PLIST_SRC=	PLIST PLIST.openxr
.endif

.include "../../graphics/tinyexr/buildlink3.mk"
.include "../../graphics/xatlas/buildlink3.mk"
.include "../../graphics/meshoptimizer/buildlink3.mk"
.if !empty(MACHINE_PLATFORM:MDarwin-*-aarch64) || !empty(MACHINE_PLATFORM:MDarwin-*-x86_64) || \
    !empty(MACHINE_PLATFORM:MLinux-*-aarch64) || !empty(MACHINE_PLATFORM:MLinux-*-x86_64) || \
    !empty(MACHINE_PLATFORM:MNetBSD-*-aarch64) || !empty(MACHINE_PLATFORM:MNetBSD-*-x86_64)
.include "../../graphics/embree/buildlink3.mk"
.endif

.include "../../graphics/qt6-qtquicktimeline/buildlink3.mk"
.include "../../graphics/qt6-qtshadertools/buildlink3.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "options.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

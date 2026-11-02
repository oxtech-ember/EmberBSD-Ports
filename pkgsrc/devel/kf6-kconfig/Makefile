# $NetBSD: Makefile,v 1.17 2026/09/06 10:05:11 markd Exp $

.include "Makefile.common"
PKGREVISION=	2

COMMENT=	Configuration system

.include "../../meta-pkgs/kde/kf6.mk"

CMAKE_CONFIGURE_ARGS+=	-DBUILD_TESTING=OFF

.include "../../mk/bsd.prefs.mk"
PLIST_VARS+=	kconfig_tools
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# Target packages retain their target-architecture copies of the generators.
CONFLICTS+=	kf6-kconfig-compiler-[0-9]*
PLIST.kconfig_tools=	yes
.else
# The native generators are installed by the matching host-tools package.
.if ${KF6VER} == "6.31.0"
DEPENDS+=	kf6-kconfig-compiler-${KF6VER}nb[1-9]*:../../devel/kf6-kconfig-compiler
.else
DEPENDS+=	kf6-kconfig-compiler-${KF6VER}{,nb[0-9]*}:../../devel/kf6-kconfig-compiler
.endif
post-install:
	${RUN}${RM} -f \
	    ${DESTDIR}${PREFIX}/libexec/kf6/kconf_update \
	    ${DESTDIR}${PREFIX}/libexec/kf6/kconfig_compiler_kf6 \
	    ${DESTDIR}${PREFIX}/lib/cmake/KF6Config/KF6ConfigCompilerTargets.cmake \
	    ${DESTDIR}${PREFIX}/lib/cmake/KF6Config/KF6ConfigCompilerTargets-noconfig.cmake
.endif

.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../devel/qt6-qttools/linguist.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

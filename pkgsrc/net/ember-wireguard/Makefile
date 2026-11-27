# EmberBSD: Qt 6 WireGuard tray over wg + wireguard-go.
DISTNAME= EmberBSD-Examples
PKGNAME= ember-wireguard-0.1.4
CATEGORIES= net
MASTER_SITES= ${MASTER_SITE_GITHUB:=oxtech-ember/}
GITHUB_PROJECT= EmberBSD-Examples
GITHUB_TAG= 15d01638198427c31db2b57ee20b4939e74a4840
WRKSRC= ${WRKDIR}/${GITHUB_PROJECT}-${GITHUB_TAG}/desktop/ember-wireguard

HOMEPAGE= https://github.com/oxtech-ember/EmberBSD-Examples/tree/${GITHUB_TAG}/desktop/ember-wireguard
COMMENT= Qt 6 manager for WireGuard tunnels via wireguard-go
LICENSE= 2-clause-bsd

USE_LANGUAGES=	c c++
USE_CXX_FEATURES= c++17
# Keep the RUNPATH from the pkgsrc link wrapper. CMake install-time
# RPATH_CHANGE fails when that wrapper RUNPATH differs from BUILD_RPATH.
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_SKIP_INSTALL_RPATH:BOOL=ON
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_SKIP_RPATH:BOOL=FALSE

DEPENDS+=	wireguard-tools-[0-9]*:../../net/wireguard-tools
DEPENDS+=	wireguard-go>=0.0.20250522nb19:../../net/wireguard-go
DEPENDS+=	qt6-qttranslations>=6.12.0nb1:../../x11/qt6-qttranslations

PKG_GROUPS+=	wireguard
OWN_DIRS+=	${PKG_SYSCONFDIR}/wireguard

SPECIAL_PERMS+=	libexec/ember-wireguard-ctl ${SETUID_ROOT_PERMS}

BUILDLINK_API_DEPENDS.kf6-kdbusaddons+=	kf6-kdbusaddons>=6.31.0
BUILDLINK_API_DEPENDS.qt6-qtbase+=	qt6-qtbase>=6.12.0

.include "../../sysutils/kf6-kdbusaddons/buildlink3.mk"
.include "../../devel/qt6-qttools/host-tools.mk"
CMAKE_CONFIGURE_ARGS+=	-DEMBER_WIREGUARD_LRELEASE:FILEPATH=${QT_HOST_PATH}/bin/lrelease
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../devel/cmake/build.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD" && ${MACHINE_ARCH} == "x86_64"
PKGREVISION=	1	# Reissue: the earlier amd64 name is in a released record.
.endif
.include "../../mk/bsd.pkg.mk"

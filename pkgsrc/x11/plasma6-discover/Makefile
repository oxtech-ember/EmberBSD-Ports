# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).

DISTNAME=	discover-${PLASMAVER}
CATEGORIES=	x11
COMMENT=	KDE Discover software manager
HOMEPAGE=	https://apps.kde.org/discover/
LICENSE=	gnu-gpl-v2 AND gnu-lgpl-v2.1 AND gnu-fdl-v1.2

.include "../../meta-pkgs/kde/plasma6.mk"

USE_TOOLS+=	msgmerge pkg-config

# PackageKit, Flatpak, Snap, Fwupd and the other Linux stores are not
# sources for this system. KNewStuff is a separate KDE catalog.
CMAKE_CONFIGURE_ARGS+=	-DBUILD_FlatpakBackend=OFF
CMAKE_CONFIGURE_ARGS+=	-DBUILD_PackageKitBackend=OFF
CMAKE_CONFIGURE_ARGS+=	-DBUILD_SnapBackend=OFF
CMAKE_CONFIGURE_ARGS+=	-DBUILD_FwupdBackend=OFF
CMAKE_CONFIGURE_ARGS+=	-DBUILD_AlpineApkBackend=OFF
CMAKE_CONFIGURE_ARGS+=	-DBUILD_RpmOstreeBackend=OFF
CMAKE_CONFIGURE_ARGS+=	-DBUILD_HoloBackend=OFF
CMAKE_CONFIGURE_ARGS+=	-DBUILD_SystemdSysupdateBackend=OFF
CMAKE_CONFIGURE_ARGS+=	-DBUILD_DummyBackend=OFF
CMAKE_CONFIGURE_ARGS+=	-DBUILD_AppStreamPreviewBackend=OFF
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_DISABLE_FIND_PACKAGE_KF6NewStuff=ON
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_DISABLE_FIND_PACKAGE_KF6Attica=ON
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_DISABLE_FIND_PACKAGE_packagekitqt6=ON
# libDiscoverCommon and libDiscoverNotifiers are installed under
# lib/plasma-discover. The executable must search that directory.
LDFLAGS+=		${COMPILER_RPATH_FLAG}${PREFIX}/lib/plasma-discover


# Snap and the AppStream preview backend are not built. Their desktop
# files would claim MIME types for those backends.
post-install:
	${RM} -f ${DESTDIR}${PREFIX}/share/applications/org.kde.discover.snap.desktop
	${RM} -f ${DESTDIR}${PREFIX}/share/applications/org.kde.discover.appstreampreview.desktop

.include "../../devel/appstream/buildlink3.mk"
.include "../../devel/kf6-kcmutils/buildlink3.mk"
.include "../../devel/kf6-kconfig/buildlink3.mk"
.include "../../devel/kf6-kcoreaddons/buildlink3.mk"
.include "../../devel/kf6-kcrash/buildlink3.mk"
.include "../../sysutils/kf6-kdbusaddons/buildlink3.mk"
.include "../../devel/kf6-ki18n/buildlink3.mk"
.include "../../devel/kf6-kidletime/buildlink3.mk"
.include "../../devel/kf6-kio/buildlink3.mk"
.include "../../devel/kf6-knotifications/buildlink3.mk"
.include "../../devel/kf6-purpose/buildlink3.mk"
.include "../../devel/qcoro/buildlink3.mk"
.include "../../archivers/kf6-karchive/buildlink3.mk"
.include "../../graphics/kf6-kiconthemes/buildlink3.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../misc/kf6-kstatusnotifieritem/buildlink3.mk"
.include "../../x11/kf6-kirigami/buildlink3.mk"
.include "../../x11/kf6-kitemviews/buildlink3.mk"
.include "../../x11/kirigami-addons/buildlink3.mk"
.include "../../x11/kf6-kxmlgui/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

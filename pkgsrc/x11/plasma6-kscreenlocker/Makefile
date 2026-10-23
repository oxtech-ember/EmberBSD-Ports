# $NetBSD: Makefile,v 1.10 2026/09/06 10:23:32 markd Exp $

DISTNAME=	kscreenlocker-${PLASMAVER}
CATEGORIES=	x11

HOMEPAGE=	https://kde.org/plasma-desktop/
COMMENT=	Library and components for secure lock screen architecture
LICENSE=	gnu-gpl-v2

.include "../../meta-pkgs/kde/plasma6.mk"

.include "../../devel/kf6-kdoctools/buildlink3.mk"
DEPENDS+=	pam-pwauth_suid>=1.2:../../security/pam-pwauth_suid

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# These commands run on the installed target, never during the host build.
CMAKE_CONFIGURE_ARGS+= -Dcklistsessions_EXECUTABLE=${PREFIX}/bin/ck-list-sessions
CMAKE_CONFIGURE_ARGS+= -Dqdbus_EXECUTABLE=${PREFIX}/qt6/bin/qdbus
pre-configure:
	${TEST} -x ${CROSS_DESTDIR}${PREFIX}/bin/ck-list-sessions
	${TEST} -x ${CROSS_DESTDIR}${PREFIX}/qt6/bin/qdbus
.endif

.include "../../devel/qt6-qttools/buildlink3.mk"

USE_TOOLS+=	msgmerge pkg-config

EGDIR=		share/examples/pam.d

CONF_FILES+=	${EGDIR}/kde ${PKG_SYSCONFBASEDIR}/pam.d/kde
MAKE_DIRS+=	${PKG_SYSCONFBASEDIR}/pam.d

USE_CXX_FEATURES+=	c++23

INSTALLATION_DIRS+=	${EGDIR}

post-install:
	sed s:%%PREFIX%%:${PREFIX}: < ${FILESDIR}/kde.pam.in > ${DESTDIR}${PREFIX}/${EGDIR}/kde

.include "../../mk/pam.buildlink3.mk"
.include "../../devel/kf6-kcmutils/buildlink3.mk"
.include "../../devel/kf6-kcrash/buildlink3.mk"
.include "../../devel/kf6-ki18n/buildlink3.mk"
.include "../../devel/kf6-kidletime/buildlink3.mk"
.include "../../devel/kf6-kio/buildlink3.mk"
.include "../../devel/kf6-knotifications/buildlink3.mk"
.include "../../devel/plasma6-kwayland/buildlink3.mk"
.include "../../graphics/kf6-ksvg/buildlink3.mk"
.include "../../sysutils/consolekit/buildlink3.mk"
.include "../../sysutils/kf6-solid/buildlink3.mk"
.include "../../x11/kf6-kglobalaccel/buildlink3.mk"
.include "../../x11/kf6-kwindowsystem/buildlink3.mk"
.include "../../x11/kf6-kxmlgui/buildlink3.mk"
.include "../../x11/plasma6-layer-shell-qt/buildlink3.mk"
.include "../../x11/plasma6-libkscreen/buildlink3.mk"
.include "../../x11/plasma6-libplasma/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

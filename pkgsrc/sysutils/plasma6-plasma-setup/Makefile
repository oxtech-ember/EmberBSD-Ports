# $NetBSD$

DISTNAME=	plasma-setup-${PLASMAVER}
CATEGORIES=	sysutils

HOMEPAGE=	https://kde.org/plasma-desktop/
COMMENT=	Initial setup wizard for Plasma
LICENSE=	gnu-lgpl-v2.1 AND gnu-gpl-v2

.include "../../meta-pkgs/kde/plasma6.mk"

USE_CXX_FEATURES+=	c++23
USE_TOOLS+=		msgmerge pkg-config

# Account creation and the boot switch call systemd over D-Bus.
# The polkit rule stays in examples and is not installed as live policy.

post-install:
	${MKDIR} ${DESTDIR}${PREFIX}/share/examples/plasma6-plasma-setup
	if [ -f ${DESTDIR}${PREFIX}/share/polkit-1/rules.d/plasma-setup-polkit.rules ]; then \
		${MV} ${DESTDIR}${PREFIX}/share/polkit-1/rules.d/plasma-setup-polkit.rules \
			${DESTDIR}${PREFIX}/share/examples/plasma6-plasma-setup/ ; \
	fi
	if [ -f ${DESTDIR}${PREFIX}/etc/xdg/plasmasetuprc ]; then \
		${MV} ${DESTDIR}${PREFIX}/etc/xdg/plasmasetuprc \
			${DESTDIR}${PREFIX}/share/examples/plasma6-plasma-setup/ ; \
	fi
	if [ -f ${DESTDIR}${PREFIX}/lib/systemd/system/plasma-setup.service ]; then \
		${MV} ${DESTDIR}${PREFIX}/lib/systemd/system/plasma-setup.service \
			${DESTDIR}${PREFIX}/share/examples/plasma6-plasma-setup/ ; \
	fi
	if [ -f ${DESTDIR}${PREFIX}/lib/sysusers.d/plasma-setup-sysuser.conf ]; then \
		${MV} ${DESTDIR}${PREFIX}/lib/sysusers.d/plasma-setup-sysuser.conf \
			${DESTDIR}${PREFIX}/share/examples/plasma6-plasma-setup/ ; \
	fi
	if [ -f ${DESTDIR}${PREFIX}/lib/tmpfiles.d/plasma-setup-tmpfiles.conf ]; then \
		${MV} ${DESTDIR}${PREFIX}/lib/tmpfiles.d/plasma-setup-tmpfiles.conf \
			${DESTDIR}${PREFIX}/share/examples/plasma6-plasma-setup/ ; \
	fi

.include "../../devel/kf6-kconfig/buildlink3.mk"
.include "../../devel/kf6-kcoreaddons/buildlink3.mk"
.include "../../devel/kf6-ki18n/buildlink3.mk"
.include "../../devel/kf6-kpackage/buildlink3.mk"
.include "../../graphics/qt6-qtsvg/buildlink3.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../security/kf6-kauth/buildlink3.mk"
.include "../../x11/plasma6-libkscreen/buildlink3.mk"
.include "../../x11/plasma6-plasma-workspace/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

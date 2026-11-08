# $NetBSD$

DISTNAME=	kwallet-pam-${PLASMAVER}
CATEGORIES=	security

HOMEPAGE=	https://kde.org/plasma-desktop/
COMMENT=	PAM module that unlocks KWallet
LICENSE=	gnu-lgpl-v2.1

.include "../../meta-pkgs/kde/plasma6.mk"

# The module is packaged. No pam.d entry is installed and the module is
# not added to a login stack. The autostart file and the systemd unit
# stay under share/examples.

USE_TOOLS+=	msgmerge pkg-config

CMAKE_CONFIGURE_ARGS+=	-DBUILD_TESTING=OFF
CMAKE_CONFIGURE_ARGS+=	-DPAM_INCLUDE_DIR=${EMBERBSD_CROSS_SYSROOT}/usr/include
CMAKE_CONFIGURE_ARGS+=	-DPAM_LIBRARY=${EMBERBSD_CROSS_SYSROOT}/usr/lib/libpam.so
CMAKE_CONFIGURE_ARGS+=	-DKWALLETD_BIN_PATH=/usr/pkg/bin/ksecretd

post-install:
	${MKDIR} ${DESTDIR}${PREFIX}/share/examples/plasma6-kwallet-pam
	if [ -f ${DESTDIR}${PREFIX}/etc/xdg/autostart/pam_kwallet_init.desktop ]; then \
		${MV} ${DESTDIR}${PREFIX}/etc/xdg/autostart/pam_kwallet_init.desktop \
			${DESTDIR}${PREFIX}/share/examples/plasma6-kwallet-pam/ ; \
	fi
	if [ -f ${DESTDIR}${PREFIX}/share/autostart/pam_kwallet_init.desktop ]; then \
		${MV} ${DESTDIR}${PREFIX}/share/autostart/pam_kwallet_init.desktop \
			${DESTDIR}${PREFIX}/share/examples/plasma6-kwallet-pam/ ; \
	fi
	if [ -f ${DESTDIR}${PREFIX}/lib/systemd/user/plasma-kwallet-pam.service ]; then \
		${MV} ${DESTDIR}${PREFIX}/lib/systemd/user/plasma-kwallet-pam.service \
			${DESTDIR}${PREFIX}/share/examples/plasma6-kwallet-pam/ ; \
	fi

.include "../../security/kf6-kwallet/buildlink3.mk"
.include "../../security/libgcrypt/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

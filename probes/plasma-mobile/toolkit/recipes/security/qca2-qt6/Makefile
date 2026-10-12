# $NetBSD: Makefile,v 1.15 2026/09/12 21:04:21 wiz Exp $

PKGNAME=	qca2-qt6-${DISTNAME:C/.*-//}

PKGREVISION=	1

COMMENT=	Cross-platform crypto API for Qt6

.include "Makefile.common"

DEPENDS+=	mozilla-rootcerts-[0-9]*:../../security/mozilla-rootcerts

INSTALLATION_DIRS=	lib/pkgconfig

CMAKE_CONFIGURE_ARGS+=	-DQT6=ON
CMAKE_CONFIGURE_ARGS+=	-DBUILD_PLUGINS=ossl
CMAKE_CONFIGURE_ARGS+=	-DQCA_MAN_INSTALL_DIR=${PREFIX}/${PKGMANDIR}

.include "../../security/openssl/buildlink3.mk"
.include "../../devel/qt6-qt5compat/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# Native qmake describes the build host, not the target Qt prefix.
CMAKE_CONFIGURE_ARGS+= -DQCA_INSTALL_IN_QT_PREFIX=OFF
CMAKE_CONFIGURE_ARGS+= -DQCA_PREFIX_INSTALL_DIR=${PREFIX}
CMAKE_CONFIGURE_ARGS+= -DUSE_RELATIVE_PATHS=ON
CMAKE_CONFIGURE_ARGS+= -DQCA_TEST_DATA_DIR=.
CMAKE_CONFIGURE_ARGS+= -DQCA_PLUGINS_INSTALL_DIR=${PREFIX}/qt6/plugins
CMAKE_CONFIGURE_ARGS+= -DQCA_BINARY_INSTALL_DIR=${PREFIX}/qt6/bin
CMAKE_CONFIGURE_ARGS+= -DQCA_LIBRARY_INSTALL_DIR=${PREFIX}/qt6/lib
CMAKE_CONFIGURE_ARGS+= -DQCA_FEATURE_INSTALL_DIR=${PREFIX}/qt6/mkspecs/features
CMAKE_CONFIGURE_ARGS+= -DQCA_INCLUDE_INSTALL_DIR=${PREFIX}/qt6/include/Qca-qt6
CMAKE_CONFIGURE_ARGS+= -DQCA_PRIVATE_INCLUDE_INSTALL_DIR=${PREFIX}/qt6/include/Qca-qt6
CMAKE_CONFIGURE_ARGS+= -DQCA_DOC_INSTALL_DIR=${PREFIX}/qt6/doc/html/qca
CMAKE_CONFIGURE_ARGS+= -DQCA_MAN_INSTALL_DIR=${PREFIX}/${PKGMANDIR}
CMAKE_CONFIGURE_ARGS+= -Dqca_CERTSTORE=${PREFIX}/share/mozilla-rootcerts/cacert.pem
# Prevent upstream's host filesystem probe from overriding the target path.
CONFIGURE_ENV+= QC_CERTSTORE_PATH=${PREFIX}/share/mozilla-rootcerts/cacert.pem

pre-configure:
	${TEST} -f ${CROSS_DESTDIR}${PREFIX}/share/mozilla-rootcerts/cacert.pem
.endif
.include "../../mk/bsd.pkg.mk"

# qt6 insists on a UTF locale, override setting C in bsd.pkg.mk
ALL_ENV+=	LANG=C.UTF-8
ALL_ENV+=	LC_ALL=C.UTF-8
ALL_ENV+=	LC_COLLATE=C.UTF-8
ALL_ENV+=	LC_CTYPE=C.UTF-8
ALL_ENV+=	LC_MESSAGES=C.UTF-8
ALL_ENV+=	LC_MONETARY=C.UTF-8
ALL_ENV+=	LC_NUMERIC=C.UTF-8
ALL_ENV+=	LC_TIME=C.UTF-8

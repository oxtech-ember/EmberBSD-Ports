# $NetBSD: Makefile,v 1.44 2026/09/02 19:04:11 wiz Exp $

PKGNAME=	poppler-qt6-${POPPLER_VERS}
COMMENT=	PDF rendering library (Qt6 wrapper)

CMAKE_CONFIGURE_ARGS+=	-DBUILD_GTK_TESTS=OFF
CMAKE_CONFIGURE_ARGS+=	-DENABLE_GLIB=OFF
CMAKE_CONFIGURE_ARGS+=	-DENABLE_UTILS=OFF
CMAKE_CONFIGURE_ARGS+=	-DENABLE_CPP=OFF
CMAKE_CONFIGURE_ARGS+=	-DENABLE_QT5=OFF
CMAKE_CONFIGURE_ARGS+=	-DENABLE_QT6=ON
# Don't build libcurl based HTTP support. ## might want to include
CMAKE_CONFIGURE_ARGS+=	-DENABLE_LIBCURL=OFF

PKGCONFIG_OVERRIDE+=	poppler-qt6.pc.cmake

INSTALLATION_DIRS+=	lib/pkgconfig

BUILD_DIRS=	qt6/src
.include "../../print/poppler/Makefile.common"

post-install:
	${INSTALL_DATA} ${WRKSRC}/${CMAKE_BUILD_DIR}/poppler-qt6.pc \
		${DESTDIR}${PREFIX}/lib/pkgconfig

BUILDLINK_API_DEPENDS.poppler+= poppler>=${POPPLER_VERS}
.include "../../print/poppler/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/pthread.buildlink3.mk"
.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} == "NetBSD" && ${MACHINE_ARCH} == "aarch64"
PKGREVISION=	1
.endif

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD" && ${MACHINE_ARCH} == "x86_64"
PKGREVISION=	1	# Reissue: the earlier amd64 name is in a released record.
.endif
.include "../../mk/bsd.pkg.mk"

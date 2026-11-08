# $NetBSD$

DISTNAME=	freerdp-3.10.3
PKGNAME=	freerdp3-3.10.3
CATEGORIES=	net
MASTER_SITES=	https://pub.freerdp.com/releases/

HOMEPAGE=	https://www.freerdp.com/
COMMENT=	Free implementation of the Remote Desktop Protocol (major version 3)
LICENSE=	apache-2.0

# A separate major version. freerdp2 stays installed and is not replaced.
# The server library is built for later KRDP linkage. No listener is started.

.include "../../devel/cmake/build.mk"

USE_TOOLS+=	pkg-config
USE_LANGUAGES=	c c++

CMAKE_CONFIGURE_ARGS+=	-DWITH_SERVER=ON
CMAKE_CONFIGURE_ARGS+=	-DWITH_CLIENT=ON
CMAKE_CONFIGURE_ARGS+=	-DWITH_CLIENT_SDL=OFF
CMAKE_CONFIGURE_ARGS+=	-DWITH_MANPAGES=OFF
CMAKE_CONFIGURE_ARGS+=	-DWITH_X11=ON
CMAKE_CONFIGURE_ARGS+=	-DWITH_ALSA=OFF
CMAKE_CONFIGURE_ARGS+=	-DWITH_PULSE=OFF
CMAKE_CONFIGURE_ARGS+=	-DWITH_CUPS=OFF
CMAKE_CONFIGURE_ARGS+=	-DWITH_GSTREAMER_1_0=OFF
CMAKE_CONFIGURE_ARGS+=	-DWITH_OSS=OFF
CMAKE_CONFIGURE_ARGS+=	-DWITH_FUSE=OFF
CMAKE_CONFIGURE_ARGS+=	-DBUILD_TESTING=OFF
# FFmpeg 9 keeps its headers and libraries outside the default search path.
# FreeRDP's finder does not use the pkg-config include directory it queries.
CMAKE_CONFIGURE_ARGS+=	-DAVCODEC_INCLUDE_DIRS=${BUILDLINK_DIR}/include/ffmpeg9
CMAKE_CONFIGURE_ARGS+=	-DAVCODEC_LIBRARIES=${BUILDLINK_DIR}/lib/ffmpeg9/libavcodec.so
CMAKE_CONFIGURE_ARGS+=	-DAVUTIL_INCLUDE_DIRS=${BUILDLINK_DIR}/include/ffmpeg9
CMAKE_CONFIGURE_ARGS+=	-DAVUTIL_LIBRARIES=${BUILDLINK_DIR}/lib/ffmpeg9/libavutil.so
CMAKE_CONFIGURE_ARGS+=	-DSWSCALE_INCLUDE_DIRS=${BUILDLINK_DIR}/include/ffmpeg9
CMAKE_CONFIGURE_ARGS+=	-DSWSCALE_LIBRARIES=${BUILDLINK_DIR}/lib/ffmpeg9/libswscale.so
CMAKE_CONFIGURE_ARGS+=	-DSWRESAMPLE_INCLUDE_DIRS=${BUILDLINK_DIR}/include/ffmpeg9
CMAKE_CONFIGURE_ARGS+=	-DSWRESAMPLE_LIBRARIES=${BUILDLINK_DIR}/lib/ffmpeg9/libswresample.so

LDFLAGS.NetBSD+=	-lexecinfo

# The buildlink pkg-config directory does not contain Heimdal's .pc file.
pre-configure:
	${MKDIR} ${BUILDLINK_DIR}/lib/pkgconfig
	${LN} -sf ${EMBERBSD_CROSS_SYSROOT}/usr/pkg/lib/pkgconfig/heimdal-krb5.pc \
		${BUILDLINK_DIR}/lib/pkgconfig/heimdal-krb5.pc
	${LN} -sf ${EMBERBSD_CROSS_SYSROOT}/usr/pkg/lib/pkgconfig/krb5.pc \
		${BUILDLINK_DIR}/lib/pkgconfig/krb5.pc

post-install:
	if [ -f ${DESTDIR}${PREFIX}/bin/xfreerdp ]; then \
		${MV} ${DESTDIR}${PREFIX}/bin/xfreerdp ${DESTDIR}${PREFIX}/bin/xfreerdp3; \
	fi
	if [ -f ${DESTDIR}${PREFIX}/bin/freerdp-proxy ]; then \
		${MV} ${DESTDIR}${PREFIX}/bin/freerdp-proxy ${DESTDIR}${PREFIX}/bin/freerdp-proxy3; \
	fi
	if [ -f ${DESTDIR}${PREFIX}/bin/freerdp-shadow-cli ]; then \
		${MV} ${DESTDIR}${PREFIX}/bin/freerdp-shadow-cli ${DESTDIR}${PREFIX}/bin/freerdp-shadow-cli3; \
	fi
	if [ -f ${DESTDIR}${PREFIX}/bin/winpr-hash ]; then \
		${MV} ${DESTDIR}${PREFIX}/bin/winpr-hash ${DESTDIR}${PREFIX}/bin/winpr-hash3; \
	fi
	if [ -f ${DESTDIR}${PREFIX}/bin/winpr-makecert ]; then \
		${MV} ${DESTDIR}${PREFIX}/bin/winpr-makecert ${DESTDIR}${PREFIX}/bin/winpr-makecert3; \
	fi
	if [ -f ${DESTDIR}${PREFIX}/lib/cmake/WinPR3/WinPRTargets-release.cmake ]; then \
		${SED} -e 's|/bin/winpr-makecert"|/bin/winpr-makecert3"|g' \
			-e 's|/bin/winpr-hash"|/bin/winpr-hash3"|g' \
			${DESTDIR}${PREFIX}/lib/cmake/WinPR3/WinPRTargets-release.cmake \
			> ${DESTDIR}${PREFIX}/lib/cmake/WinPR3/WinPRTargets-release.cmake.tmp && \
		${MV} ${DESTDIR}${PREFIX}/lib/cmake/WinPR3/WinPRTargets-release.cmake.tmp \
			${DESTDIR}${PREFIX}/lib/cmake/WinPR3/WinPRTargets-release.cmake; \
	fi

.include "../../textproc/icu/buildlink3.mk"
.include "../../devel/libusb1/buildlink3.mk"
.include "../../devel/zlib/buildlink3.mk"
.include "../../multimedia/ffmpeg9/buildlink3.mk"
.include "../../security/heimdal/buildlink3.mk"
.include "../../security/openssl/buildlink3.mk"
.include "../../mk/jpeg.buildlink3.mk"
.include "../../x11/libxkbfile/buildlink3.mk"
.include "../../x11/libX11/buildlink3.mk"
.include "../../x11/libXcursor/buildlink3.mk"
.include "../../x11/libXext/buildlink3.mk"
.include "../../x11/libXfixes/buildlink3.mk"
.include "../../x11/libXi/buildlink3.mk"
.include "../../x11/libXinerama/buildlink3.mk"
.include "../../x11/libXrandr/buildlink3.mk"
.include "../../x11/libXrender/buildlink3.mk"
.include "../../x11/libxkbcommon/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

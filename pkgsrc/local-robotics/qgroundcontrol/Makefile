# $NetBSD$
# Origin: EmberBSD contributors (AI-assisted).

DISTNAME=	qgroundcontrol-5.1.5
CATEGORIES=	local-robotics
MASTER_SITES=	${MASTER_SITE_GITHUB:=mavlink/}
GITHUB_PROJECT=	qgroundcontrol
GITHUB_TAG=	v${PKGVERSION_NOREV}
DIST_SUBDIR=	qgroundcontrol

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://qgroundcontrol.com/
COMMENT=	Ground control station for MAVLink vehicles
# QGroundControl is GPL-3.0 or Apache-2.0. The ArduPilot parameter data is
# GPL-3.0. The other licenses apply to the pinned sources below.
LICENSE=	gnu-gpl-v3 AND gnu-lgpl-v3 AND gnu-lgpl-v2.1 AND mit AND \
		modified-bsd AND 2-clause-bsd AND apache-2.0 AND boost-license AND \
		isc AND zlib

# QGroundControl 5.1.5 downloads these sources with CPM during configure.
# Pin each one to the revision that the v5.1.5 tag selects. ArduPilot's
# parameter repository is tracked at "main" upstream; use its last commit
# before the v5.1.5 tag (2026-09-30).
QGC_MAVLINK=		c409cf690454db6d3e004bd14173bc6c7ff1e0ff
QGC_PYMAVLINK=		5977f44504f01715a44bed44a4601e6c12cef92d
QGC_LIBEVENTS=		840a88ea226d4eb0fd4c391ce860317422756435
QGC_GPSDRIVERS=		cd6f506afda9bd6e8e4645f094dcf5415f1f8be4
QGC_APM_PARAMS=		738bda9d20fa9ea3ae408d6a64d14db6c1e27494
QGC_SDL_GCDB=		513c72e34569e0f471dde7aa26eecb23946c3ef7
QGC_EARCUT=		f36ced7e50254738c4e5af1a239f5fb7b1094007

DISTFILES=	${DISTNAME}.tar.gz
SITES.${DISTNAME}.tar.gz= \
	-https://github.com/mavlink/qgroundcontrol/archive/refs/tags/${GITHUB_TAG}.tar.gz

# Distfile, GitHub path, extracted directory, CPM package name.
QGC_DEPS=	mavlink-${QGC_MAVLINK}.tar.gz \
		    mavlink/mavlink/archive/${QGC_MAVLINK}.tar.gz \
		    mavlink-${QGC_MAVLINK} mavlink
QGC_DEPS+=	valijson-1.1.0.tar.gz \
		    tristanpenman/valijson/archive/refs/tags/v1.1.0.tar.gz \
		    valijson-1.1.0 valijson
QGC_DEPS+=	geographiclib-2.7.tar.gz \
		    geographiclib/geographiclib/archive/refs/tags/r2.7.tar.gz \
		    geographiclib-r2.7 geographiclib
QGC_DEPS+=	ulog_cpp-1.0.1.tar.gz \
		    PX4/ulog_cpp/archive/refs/tags/v1.0.1.tar.gz \
		    ulog_cpp-1.0.1 ulog_cpp
QGC_DEPS+=	libevents-${QGC_LIBEVENTS}.tar.gz \
		    mavlink/libevents/archive/${QGC_LIBEVENTS}.tar.gz \
		    libevents-${QGC_LIBEVENTS} libevents
QGC_DEPS+=	PX4-GPSDrivers-${QGC_GPSDRIVERS}.tar.gz \
		    PX4/PX4-GPSDrivers/archive/${QGC_GPSDRIVERS}.tar.gz \
		    PX4-GPSDrivers-${QGC_GPSDRIVERS} px4-gpsdrivers
QGC_DEPS+=	ParameterRepository-${QGC_APM_PARAMS}.tar.gz \
		    ArduPilot/ParameterRepository/archive/${QGC_APM_PARAMS}.tar.gz \
		    ParameterRepository-${QGC_APM_PARAMS} ArduPilotParams
QGC_DEPS+=	SDL_GameControllerDB-${QGC_SDL_GCDB}.tar.gz \
		    mdqinc/SDL_GameControllerDB/archive/${QGC_SDL_GCDB}.tar.gz \
		    SDL_GameControllerDB-${QGC_SDL_GCDB} sdl_gamecontrollerdb
QGC_DEPS+=	shapelib-1.6.3.tar.gz \
		    OSGeo/shapelib/archive/refs/tags/v1.6.3.tar.gz \
		    shapelib-1.6.3 Shapelib
QGC_DEPS+=	libexif-0.6.26.tar.gz \
		    libexif/libexif/archive/refs/tags/v0.6.26.tar.gz \
		    libexif-0.6.26 libexif
QGC_DEPS+=	protozero-1.8.1.tar.gz \
		    mapbox/protozero/archive/refs/tags/v1.8.1.tar.gz \
		    protozero-1.8.1 protozero
QGC_DEPS+=	libosmium-2.23.0.tar.gz \
		    osmcode/libosmium/archive/refs/tags/v2.23.0.tar.gz \
		    libosmium-2.23.0 libosmium
QGC_DEPS+=	earcut.hpp-${QGC_EARCUT}.tar.gz \
		    mapbox/earcut.hpp/archive/${QGC_EARCUT}.tar.gz \
		    earcut.hpp-${QGC_EARCUT} earcut_hpp

.for file path dir name in ${QGC_DEPS}
DISTFILES+=		${file}
SITES.${file}=		-https://github.com/${path}
QGC_DEP_DIRS+=		${dir}:${name}
CMAKE_CONFIGURE_ARGS+=	-DCPM_${name}_SOURCE:PATH=${WRKSRC}/pkgsrc-deps/${name}
.endfor

# pymavlink is a Git submodule of mavlink; the mavlink archive omits it.
DISTFILES+=	pymavlink-${QGC_PYMAVLINK}.tar.gz
SITES.pymavlink-${QGC_PYMAVLINK}.tar.gz= \
	-https://github.com/ArduPilot/pymavlink/archive/${QGC_PYMAVLINK}.tar.gz

USE_LANGUAGES=		c c++
USE_CXX_FEATURES=	c++20
USE_TOOLS+=		pkg-config
# Some resource file names contain a space; generated Makefiles cannot
# name them. Ninja can.
CMAKE_GENERATOR=	ninja

CMAKE_CONFIGURE_ARGS+=	-DCMAKE_BUILD_TYPE=Release
CMAKE_CONFIGURE_ARGS+=	-DQGC_USE_SYSTEM_LIBS=ON
CMAKE_CONFIGURE_ARGS+=	-DQGC_QT_MAXIMUM_VERSION=6.12.0
CMAKE_CONFIGURE_ARGS+=	-DQGC_BUILD_INSTALLER=OFF
CMAKE_CONFIGURE_ARGS+=	-DQGC_CREATE_APPIMAGE=OFF
CMAKE_CONFIGURE_ARGS+=	-DQGC_CPACK_GENERATOR=
CMAKE_CONFIGURE_ARGS+=	-DQGC_UPDATE_TRACKED_DEPS=OFF
CMAKE_CONFIGURE_ARGS+=	-DQGC_AUTO_PYTHON_VENV=OFF
CMAKE_CONFIGURE_ARGS+=	-DQGC_USE_CACHE=OFF
CMAKE_CONFIGURE_ARGS+=	-DQGC_USE_MOCCACHE=OFF
CMAKE_CONFIGURE_ARGS+=	-DQGC_ENABLE_WERROR=OFF
CMAKE_CONFIGURE_ARGS+=	-DQGC_ENABLE_GST_VIDEOSTREAMING=ON
CMAKE_CONFIGURE_ARGS+=	-DMAVLINK_USE_PREINSTALLED_PYTHON=ON
CMAKE_CONFIGURE_ARGS+=	-DFETCHCONTENT_FULLY_DISCONNECTED=ON
CMAKE_CONFIGURE_ARGS+=	-DPython3_EXECUTABLE:FILEPATH=${TOOL_PYTHONBIN}
CMAKE_CONFIGURE_ARGS+=	-DPython_EXECUTABLE:FILEPATH=${TOOL_PYTHONBIN}
# QGC looks for lib/gstreamer-1.0 below this root; in a cross build it is
# the target root.
CMAKE_CONFIGURE_ARGS+=	-DGStreamer_ROOT_DIR:PATH=${_CROSS_DESTDIR}${BUILDLINK_PREFIX.gstreamer1}

PYTHON_FOR_BUILD_ONLY=	tool
TOOL_DEPENDS+=	${PYPKGPREFIX}-lxml-[0-9]*:../../textproc/py-lxml
TOOL_DEPENDS+=	${PYPKGPREFIX}-jinja2-[0-9]*:../../textproc/py-jinja2
TOOL_DEPENDS+=	${PYPKGPREFIX}-defusedxml-[0-9]*:../../textproc/py-defusedxml

# Runtime plugins: image formats for map tiles, GStreamer video elements.
DEPENDS+=	qt6-qtimageformats-[0-9]*:../../graphics/qt6-qtimageformats
DEPENDS+=	gst-plugins1-good-[0-9]*:../../multimedia/gst-plugins1-good
DEPENDS+=	gst-plugins1-gl-[0-9]*:../../graphics/gst-plugins1-gl

INSTALLATION_DIRS=	bin libexec/qgroundcontrol share/applications
INSTALLATION_DIRS+=	share/icons/hicolor/scalable/apps
INSTALLATION_DIRS+=	share/icons/hicolor/256x256/apps
INSTALLATION_DIRS+=	share/doc/qgroundcontrol

# The tag archive omits .github (export-ignore). CMake reads the pinned
# versions from .github/build-config.json; files/ has the v5.1.5 copy.
post-extract:
	${MKDIR} ${WRKSRC}/.github
	${CP} ${FILESDIR}/build-config.json ${WRKSRC}/.github/build-config.json
	${MKDIR} ${WRKSRC}/pkgsrc-deps
.for pair in ${QGC_DEP_DIRS}
	${MV} ${WRKDIR}/${pair:C/:.*//} ${WRKSRC}/pkgsrc-deps/${pair:C/.*://}
.endfor
	${RMDIR} ${WRKSRC}/pkgsrc-deps/mavlink/pymavlink
	${MV} ${WRKDIR}/pymavlink-${QGC_PYMAVLINK} \
	    ${WRKSRC}/pkgsrc-deps/mavlink/pymavlink
# CPM applies these QGroundControl patches after a download. A local
# CPM_<name>_SOURCE skips them, so apply them here.
.for dir patch in valijson src/Utilities/Parsing/valijson-qtjson-int64.patch \
	geographiclib src/Utilities/Geo/geographiclib.patch \
	mavlink src/MAVLink/mavlink-deterministic-mavgen.patch
	${PATCH} -s -p1 -d ${WRKSRC}/pkgsrc-deps/${dir} < ${WRKSRC}/${patch}
.endfor

QGC_LICENSES=	LICENSE-GPL LICENSE-APACHE \
		pkgsrc-deps/mavlink/COPYING:mavlink-COPYING \
		pkgsrc-deps/mavlink/pymavlink/COPYING:pymavlink-COPYING \
		pkgsrc-deps/valijson/LICENSE:valijson-LICENSE \
		pkgsrc-deps/geographiclib/LICENSE.txt:geographiclib-LICENSE.txt \
		pkgsrc-deps/ulog_cpp/LICENSE:ulog_cpp-LICENSE \
		pkgsrc-deps/libevents/LICENSE.md:libevents-LICENSE.md \
		pkgsrc-deps/px4-gpsdrivers/LICENSE.md:px4-gpsdrivers-LICENSE.md \
		pkgsrc-deps/Shapelib/LICENSE-MIT:shapelib-LICENSE-MIT \
		pkgsrc-deps/libexif/COPYING:libexif-COPYING \
		pkgsrc-deps/protozero/LICENSE.md:protozero-LICENSE.md \
		pkgsrc-deps/libosmium/LICENSE:libosmium-LICENSE \
		pkgsrc-deps/earcut_hpp/LICENSE:earcut-LICENSE \
		pkgsrc-deps/protozero/LICENSE.from_folly:protozero-LICENSE.from_folly \
		pkgsrc-deps/sdl_gamecontrollerdb/LICENSE:sdl_gamecontrollerdb-LICENSE

do-install:
	${INSTALL_PROGRAM} ${WRKSRC}/${CMAKE_BUILD_DIR}/Release/QGroundControl \
	    ${DESTDIR}${PREFIX}/libexec/qgroundcontrol/QGroundControl
	${SED} -e 's,@PREFIX@,${PREFIX},g' ${FILESDIR}/qgroundcontrol.sh \
	    > ${WRKDIR}/qgroundcontrol
	${INSTALL_SCRIPT} ${WRKDIR}/qgroundcontrol ${DESTDIR}${PREFIX}/bin/qgroundcontrol
	${INSTALL_DATA} ${FILESDIR}/qgroundcontrol.desktop \
	    ${DESTDIR}${PREFIX}/share/applications/qgroundcontrol.desktop
	${INSTALL_DATA} ${WRKSRC}/deploy/linux/QGroundControl.svg \
	    ${DESTDIR}${PREFIX}/share/icons/hicolor/scalable/apps/qgroundcontrol.svg
	${INSTALL_DATA} ${WRKSRC}/deploy/linux/QGroundControl_256.png \
	    ${DESTDIR}${PREFIX}/share/icons/hicolor/256x256/apps/qgroundcontrol.png
.for pair in ${QGC_LICENSES}
	${INSTALL_DATA} ${WRKSRC}/${pair:C/:.*//} \
	    ${DESTDIR}${PREFIX}/share/doc/qgroundcontrol/${pair:C/.*://}
.endfor

.include "../../x11/qt6-qtbase/host-tools.mk"
.include "../../lang/qt6-qtdeclarative/host-tools.mk"
.include "../../graphics/qt6-qtshadertools/host-tools.mk"
.include "../../graphics/qt6-qtquick3d/host-tools.mk"
.include "../../devel/qt6-qttools/host-tools.mk"
.include "../../lang/python/tool.mk"
.include "../../devel/cmake/build.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../geography/qt6-qtlocation/buildlink3.mk"
.include "../../geography/qt6-qtpositioning/buildlink3.mk"
.include "../../multimedia/qt6-qtmultimedia/buildlink3.mk"
.if ${OPSYS} == "NetBSD"
# nb1 lists the NetBSD dty* serial and USB modem devices for QGC.
BUILDLINK_API_DEPENDS.qt6-qtserialport+=	qt6-qtserialport>=6.12.0nb1
.endif
.include "../../x11/qt6-qtserialport/buildlink3.mk"
.include "../../graphics/qt6-qtsvg/buildlink3.mk"
.include "../../audio/qt6-qtspeech/buildlink3.mk"
.include "../../misc/qt6-qtsensors/buildlink3.mk"
.include "../../net/qt6-qtwebsockets/buildlink3.mk"
.include "../../www/qt6-qthttpserver/buildlink3.mk"
.include "../../comms/qt6-qtconnectivity/buildlink3.mk"
.include "../../lang/qt6-qtscxml/buildlink3.mk"
.include "../../graphics/qt6-qtquick3d/buildlink3.mk"
.include "../../graphics/qt6-qtgraphs/buildlink3.mk"
.include "../../graphics/qt6-qtshadertools/buildlink3.mk"
.include "../../multimedia/gstreamer1/buildlink3.mk"
.include "../../multimedia/gst-plugins1-base/buildlink3.mk"
.include "../../devel/SDL3/buildlink3.mk"
.include "../../archivers/zstd/buildlink3.mk"
.include "../../archivers/xz/buildlink3.mk"
.include "../../textproc/expat/buildlink3.mk"
.include "../../devel/glib2/buildlink3.mk"
.include "../../x11/libxkbcommon/buildlink3.mk"
.include "../../devel/zlib/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

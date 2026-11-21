# $NetBSD: Makefile,v 1.7 2026/09/02 19:04:49 wiz Exp $

DISTNAME=	libical-4.0.8
PKGNAME=	${DISTNAME:S/libical/libical4/}
CATEGORIES=	time
MASTER_SITES=	${MASTER_SITE_GITHUB:=libical/}
GITHUB_PROJECT=	libical
GITHUB_RELEASE=	v${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/libical/libical
COMMENT=	Reference implementation of the iCalendar data type and format (v4)
LICENSE=	gnu-lgpl-v2.1 OR mpl-2.0

TOOL_DEPENDS+=	glib2-introspection-[0-9]*:../../devel/glib2-introspection

CONFLICTS=	libical-[0-9]*

USE_TOOLS+=	perl pkg-config

USE_CC_FEATURES=	c11
USE_CXX_FEATURES=	c++11

CMAKE_CONFIGURE_ARGS+=	-DUSE_BUILTIN_TZDATA=OFF
CMAKE_CONFIGURE_ARGS+=	-DICAL_BUILD_DOCS=OFF
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_DISABLE_FIND_PACKAGE_BerkeleyDB=ON
CMAKE_CONFIGURE_ARGS+=	-DLIBICAL_JAVA_BINDINGS=False
CMAKE_CONFIGURE_ARGS+=	-DLIBICAL_GLIB_BUILD_DOCS=False

PKGCONFIG_OVERRIDE+=	libical.pc.in
PKGCONFIG_OVERRIDE+=	src/libical-glib/libical-glib.pc.in

.include "../../mk/bsd.prefs.mk"

# Native GLib and libxml2 use @rpath install names on Darwin. The CMake
# generator is executed from the build tree and also installed for cross use.
.if ${OPSYS} == "Darwin"
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_BUILD_RPATH=${LOCALBASE}/lib
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_RPATH=${LOCALBASE}/lib
.endif

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
TOOL_DEPENDS+=	libical4-${PKGVERSION_NOREV}{,nb[0-9]*}:../../time/libical4
LIBICAL4_HOST_GENERATOR_CMAKE?=	${TOOLBASE}/lib/cmake/LibIcal/IcalGlibSrcGenerator.cmake
CMAKE_CONFIGURE_ARGS+=	-DIMPORT_ICAL_GLIB_SRC_GENERATOR=${LIBICAL4_HOST_GENERATOR_CMAKE:Q}
EMBERBSD_GI_MESON_OPTIONS=	no
.include "../../devel/gobject-introspection/cross.mk"
CMAKE_CONFIGURE_ARGS+=	-DPKG_CONFIG_EXECUTABLE:FILEPATH=${WRKDIR}/.meson-gi-pkg-config
.endif

.if ${OPSYS} == "NetBSD"
# zone.tab file in /usr/share/zoneinfo
DEPENDS+=	zonetab-[0-9]*:../../time/zonetab
.endif

# C++ is only needed for test
USE_LANGUAGES=	c c++
TEST_ENV+=	LD_LIBRARY_PATH=${WRKSRC}/${CMAKE_BUILD_DIR}/lib
TEST_TARGET=	test

.include "../../devel/cmake/build.mk"
.include "../../devel/gettext-lib/buildlink3.mk"
.include "../../devel/glib2/buildlink3.mk"
.include "../../devel/gobject-introspection/buildlink3.mk"
.include "../../textproc/icu/buildlink3.mk"
.include "../../textproc/libxml2/buildlink3.mk"
.include "../../mk/pthread.buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

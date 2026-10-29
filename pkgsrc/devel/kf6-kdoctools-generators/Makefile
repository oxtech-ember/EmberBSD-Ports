# $NetBSD$
# Origin: EmberBSD (AI-assisted). Native KDocTools generators for cross builds.

DISTNAME=	kdoctools-${KF6VER}
PKGNAME=	kf6-kdoctools-generators-${KF6VER}
CATEGORIES=	devel

HOMEPAGE=	https://community.kde.org/Frameworks
COMMENT=	Native KDocTools generators for cross-built KDE documentation
LICENSE=	gnu-lgpl-v2.1

# The same release, distfile and patches as the target devel/kf6-kdoctools.
DISTINFO_FILE=	${.CURDIR}/../../devel/kf6-kdoctools/distinfo
PATCHDIR=	${.CURDIR}/../../devel/kf6-kdoctools/patches

.include "../../meta-pkgs/kde/kf6.mk"

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
PKG_FAIL_REASON+=	"${PKGNAME} is a build-host tool; build it natively"
.endif

# meinproc6, checkXML6 and docbookl10nhelper with the DocBook customization
# data they read and their CMake import. Translated messages and manuals
# belong to the target package; the generators need no KI18n.
CMAKE_CONFIGURE_ARGS+=	-DBUILD_TESTING=OFF
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_DISABLE_FIND_PACKAGE_KF6I18n=ON
CMAKE_CONFIGURE_ARGS+=	-DINSTALL_INTERNAL_TOOLS=ON

# Both install the same native files.
CONFLICTS+=	kf6-kdoctools-[0-9]*

USE_TOOLS+=	perl

TOOL_DEPENDS+=	p5-URI-[0-9]*:../../www/p5-URI
DEPENDS+=	docbook-xsl-[0-9]*:../../textproc/docbook-xsl

# Upstream installs a platform-dependent library name and data set.
GENERATE_PLIST+=	cd ${DESTDIR}${PREFIX} && \
			${FIND} * \( -type f -o -type l \) -print | ${SORT};

post-install:
.for program in meinproc6 checkXML6 docbookl10nhelper
	${RUN}${TEST} -x ${DESTDIR}${PREFIX}/bin/${program}
.endfor
	${RUN}${TEST} -r ${DESTDIR}${PREFIX}/lib/cmake/KF6DocTools/KF6DocToolsToolsTargets.cmake
	${RUN}${GREP} -q 'set(PACKAGE_VERSION "${KF6VER}")' \
	    ${DESTDIR}${PREFIX}/lib/cmake/KF6DocTools/KF6DocToolsConfigVersion.cmake

.include "../../archivers/kf6-karchive/buildlink3.mk"
.include "../../textproc/libxslt/buildlink3.mk"
.include "../../textproc/libxml2/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

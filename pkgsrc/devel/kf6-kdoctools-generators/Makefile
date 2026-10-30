# $NetBSD$
# Origin: EmberBSD (AI-assisted). Native KDocTools generators for cross builds.

PKGNAME=	kf6-kdoctools-generators-${KF6VER}

COMMENT=	Native KDocTools generators for cross-built KDE documentation

.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes"
# The Darwin wrapper already adds the final prefix RPATH during linking.
CMAKE_CONFIGURE_ARGS+= -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON
PKGREVISION= 1
.if ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
DEPENDS+= libcxx>=23.1.4nb1:../../lang/libcxx
BUILD_DEFS+= EMBERBSD_NATIVE_CXX_ABI_NAMESPACE
.endif
.endif

# The same release, distfile and patches as the target devel/kf6-kdoctools.
.include "../../devel/kf6-kdoctools/Makefile.common"

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

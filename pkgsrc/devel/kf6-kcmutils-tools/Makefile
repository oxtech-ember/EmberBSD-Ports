# $NetBSD$
# Origin: EmberBSD (AI-assisted). Native KCMUtils desktop file generator for
# cross builds of KDE packages.

.include "../../devel/kf6-kcmutils/Makefile.common"

PKGNAME=	kf6-kcmutils-tools-${KF6VER}
COMMENT=	Native KCMUtils desktop file generator for cross builds

.include "../../meta-pkgs/kde/kf6.mk"

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
PKG_FAIL_REASON+=	"${PKGNAME} is a build-host tool; build it natively"
.endif

# Upstream's QtCore-only tools build.
CMAKE_CONFIGURE_ARGS+=	-DBUILD_TESTING=OFF
CMAKE_CONFIGURE_ARGS+=	-DTOOLS_ONLY=ON

# Both install the generator and its CMake import.
CONFLICTS+=	kf6-kcmutils-[0-9]*

post-install:
	${RUN}${TEST} -x ${DESTDIR}${PREFIX}/libexec/kf6/kcmdesktopfilegenerator
	${RUN}${GREP} -q 'KF6::kcmdesktopfilegenerator' \
	    ${DESTDIR}${PREFIX}/lib/cmake/KF6KCMUtils/KF6KCMUtilsToolingTargets.cmake

# CMake names the import of the configured build type.
GENERATE_PLIST+=	cd ${DESTDIR}${PREFIX} && \
			${FIND} * \( -type f -o -type l \) -print | ${SORT};

.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

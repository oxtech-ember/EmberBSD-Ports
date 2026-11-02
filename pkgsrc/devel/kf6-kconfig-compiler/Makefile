# $NetBSD$
# Origin: EmberBSD (AI-assisted). Native KConfig code generators for cross
# builds of KDE packages.

.include "../../devel/kf6-kconfig/Makefile.common"

PKGNAME=	kf6-kconfig-compiler-${KF6VER}
PKGREVISION=	1
COMMENT=	Native KConfig code generators for cross builds

.include "../../meta-pkgs/kde/kf6.mk"

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
PKG_FAIL_REASON+=	"${PKGNAME} is a build-host tool; build it natively"
.endif

# Upstream's QtCore-only configuration. KConfigCore is linked statically, so
# the package holds only the two programs and their CMake import.
CMAKE_CONFIGURE_ARGS+=	-DBUILD_TESTING=OFF
CMAKE_CONFIGURE_ARGS+=	-DBUILD_SHARED_LIBS=OFF
CMAKE_CONFIGURE_ARGS+=	-DKCONFIG_USE_GUI=OFF
CMAKE_CONFIGURE_ARGS+=	-DKCONFIG_USE_QML=OFF
CMAKE_CONFIGURE_ARGS+=	-DUSE_DBUS=OFF

# Older full KConfig packages contain these same files. The revised native
# package now depends on this disjoint tools package; target packages carry the
# reverse conflict.
CONFLICTS+=	kf6-kconfig<6.31.0nb2

_EMBER_KCONFIG_TOOLS=	libexec/kf6/kconfig_compiler_kf6 libexec/kf6/kconf_update

post-install:
	${RUN}cd ${DESTDIR}${PREFIX} && ${FIND} . \( -type f -o -type l \) \
	    ! -path ./libexec/kf6/kconfig_compiler_kf6 \
	    ! -path ./libexec/kf6/kconf_update \
	    ! -path './lib/cmake/KF6Config/KF6ConfigCompilerTargets*.cmake' \
	    -exec ${RM} -f {} +
	${RUN}cd ${DESTDIR}${PREFIX} && ${FIND} . -depth -type d -empty -exec ${RMDIR} {} \;
.for program in ${_EMBER_KCONFIG_TOOLS}
	${RUN}${TEST} -x ${DESTDIR}${PREFIX}/${program}
.endfor
	${RUN}${GREP} -q 'KF6::kconfig_compiler' \
	    ${DESTDIR}${PREFIX}/lib/cmake/KF6Config/KF6ConfigCompilerTargets.cmake
	${RUN}${GREP} -q 'KF6::kconf_update' \
	    ${DESTDIR}${PREFIX}/lib/cmake/KF6Config/KF6ConfigCompilerTargets.cmake

# CMake names the import of the configured build type.
GENERATE_PLIST+=	cd ${DESTDIR}${PREFIX} && \
			${FIND} * \( -type f -o -type l \) -print | ${SORT};

.include "../../devel/qt6-qttools/linguist.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

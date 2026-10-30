# $NetBSD$
# Origin: EmberBSD (AI-assisted). Native KAuth policy generator for cross
# builds of KDE packages.

.include "../../security/kf6-kauth/Makefile.common"

PKGNAME=	kf6-kauth-policy-gen-${KF6VER}
COMMENT=	Native KAuth policy generator for cross builds

.include "../../meta-pkgs/kde/kf6.mk"

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
PKG_FAIL_REASON+=	"${PKGNAME} is a build-host tool; build it natively"
.endif

# Upstream's generator-only build for the Polkit backend of the targets; the
# D-Bus helper backend is off (patch-CMakeLists.txt), so only QtCore is used.
CMAKE_CONFIGURE_ARGS+=	-DBUILD_TESTING=OFF
CMAKE_CONFIGURE_ARGS+=	-DKAUTH_BUILD_CODEGENERATOR_ONLY=ON
CMAKE_CONFIGURE_ARGS+=	-DKAUTH_BACKEND_NAME=POLKITQT6-1
CMAKE_CONFIGURE_ARGS+=	-DKAUTH_HELPER_BACKEND_NAME=FAKE

# Both install the generator and its CMake import.
CONFLICTS+=	kf6-kauth-[0-9]*

post-install:
	${RUN}cd ${DESTDIR}${PREFIX} && ${FIND} . \( -type f -o -type l \) \
	    ! -path ./libexec/kf6/kauth/kauth-policy-gen \
	    ! -path './lib/cmake/KF6Auth/KF6AuthToolsTargets*.cmake' \
	    -exec ${RM} -f {} +
	${RUN}cd ${DESTDIR}${PREFIX} && ${FIND} . -depth -type d -empty -exec ${RMDIR} {} \;
	${RUN}${TEST} -x ${DESTDIR}${PREFIX}/libexec/kf6/kauth/kauth-policy-gen
	${RUN}${GREP} -q 'KF6::kauth-policy-gen' \
	    ${DESTDIR}${PREFIX}/lib/cmake/KF6Auth/KF6AuthToolsTargets.cmake

# CMake names the import of the configured build type.
GENERATE_PLIST+=	cd ${DESTDIR}${PREFIX} && \
			${FIND} * \( -type f -o -type l \) -print | ${SORT};

.include "../../devel/qt6-qttools/linguist.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

# $NetBSD$
# Origin: EmberBSD (AI-assisted). Native Breeze Icons generators for cross builds.

PKGNAME=	breeze-icons-generators-${KF6VER}

COMMENT=	Native Breeze Icons generators for cross-built icon themes

# The same release, distfile and patches as the target graphics/breeze-icons.
.include "../../graphics/breeze-icons/Makefile.common"

.include "../../meta-pkgs/kde/kf6.mk"

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
PKG_FAIL_REASON+=	"${PKGNAME} is a build-host tool; build it natively"
.endif

# Only the two generators: no icons, no icon library, no tests.
CMAKE_CONFIGURE_ARGS+=	-DBUILD_TESTING=OFF
CMAKE_CONFIGURE_ARGS+=	-DINSTALL_HOST_TOOLS=ON
CMAKE_CONFIGURE_ARGS+=	-DSKIP_INSTALL_ICONS=ON
CMAKE_CONFIGURE_ARGS+=	-DWITH_ICONS_LIBRARY=OFF
CMAKE_CONFIGURE_ARGS+=	-DWITH_ICON_GENERATION=OFF

# Both install the same native generators.
CONFLICTS+=	breeze-icons-[0-9]*

.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

# $NetBSD$
#
# Origin: EmberBSD (AI-assisted). Native Fcitx5 dictionary compiler for cross
# builds of inputmethod/fcitx5.

.include "../../inputmethod/fcitx5/Makefile.common"

PKGNAME=	${DISTNAME:S/^fcitx5-/fcitx5-comp-spell-dict-/}
COMMENT=	Fcitx5 spell dictionary compiler for cross builds

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
PKG_FAIL_REASON+=	"${PKGNAME} is a build-host tool; build it natively"
.endif

USE_TOOLS+=		msgfmt msgmerge pkg-config
USE_LANGUAGES=		c c++
USE_CXX_FEATURES+=	c++20

# Only the generator and a static Utils library are built. These choices do
# not change any feature of the target package.
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_BUILD_TYPE=Release
CMAKE_CONFIGURE_ARGS+=	-DBUILD_SHARED_LIBS=OFF
CMAKE_CONFIGURE_ARGS+=	-DBUILD_SPELL_DICT=ON
.for f in X11 WAYLAND DBUS SERVER KEYBOARD EMOJI ENCHANT LIBUUID TEST TESTING_ADDONS DOC XDGAUTOSTART
CMAKE_CONFIGURE_ARGS+=	-DENABLE_${f}=OFF
.endfor
CMAKE_CONFIGURE_ARGS+=	-DUSE_SYSTEMD=OFF
CMAKE_CONFIGURE_ARGS+=	-DEVENT_LOOP_BACKEND=none
CMAKE_CONFIGURE_ARGS+=	-DGETTEXT_MSGFMT_EXECUTABLE:FILEPATH=${TOOLS_PATH.msgfmt:Q}
CMAKE_CONFIGURE_ARGS+=	-DGETTEXT_MSGMERGE_EXECUTABLE:FILEPATH=${TOOLS_PATH.msgmerge:Q}
BUILD_TARGET=		comp-spell-dict

INSTALLATION_DIRS=	bin

do-install:
	${INSTALL_PROGRAM} ${WRKSRC}/${CMAKE_BUILD_DIR}/bin/comp-spell-dict \
	    ${DESTDIR}${PREFIX}/bin/fcitx5-comp-spell-dict

.include "../../devel/cmake/build.mk"
.include "../../devel/extra-cmake-modules/buildlink3.mk"
.include "../../devel/gettext-lib/buildlink3.mk"
.if ${USE_BUILTIN.gettext:tl} == "yes"
CMAKE_CONFIGURE_ARGS+=	-DLibIntl_INCLUDE_DIR=${BUILDLINK_PREFIX.gettext}/include
.else
CMAKE_CONFIGURE_ARGS+=	-DLibIntl_INCLUDE_DIR=${BUILDLINK_DIR}/include
.endif
.include "../../devel/libexecinfo/buildlink3.mk"
.include "../../mk/pthread.buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

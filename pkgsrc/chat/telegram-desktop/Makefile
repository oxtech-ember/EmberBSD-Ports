# $NetBSD$

.include "../telegram-desktop/Makefile.common"
PKGNAME= telegram-desktop-${TDESKTOP_VERSION}

HOMEPAGE=	https://desktop.telegram.org/
COMMENT=	Telegram Desktop messaging client
LICENSE=	gnu-gpl-v3

# Incomplete providers and system-library selection are documented in README.md.
# Remove this only after the graph and packaged-only consumer checks pass.
.if !defined(TELEGRAM_API_TEST) || ${TELEGRAM_API_TEST:tl} != "yes"
BROKEN=		Telegram Desktop dependency integration is incomplete
.endif

# Keep the client and libfido2 on the same common OpenSSL provider.
USE_BUILTIN.openssl= no
USE_LANGUAGES=	c c++
USE_CXX_FEATURES+=	c++20
USE_TOOLS+=	pkg-config gdbus-codegen
CMAKE_CONFIGURE_ARGS+=	-DDESKTOP_APP_USE_PACKAGED=ON
CMAKE_CONFIGURE_ARGS+=	-DTDESKTOP_USE_MINIZIP_NG=ON
CMAKE_CONFIGURE_ARGS+=	-DDESKTOP_APP_DISABLE_AUTOUPDATE=ON
CMAKE_CONFIGURE_ARGS+=	-DDESKTOP_APP_DISABLE_QT_PLUGINS=ON
CMAKE_CONFIGURE_ARGS+=	-DQT_VERSION_MAJOR=6
CMAKE_CONFIGURE_ARGS+=	-DDESKTOP_APP_CPPGIR_EXECUTABLE=${TOOLBASE}/bin/cppgir
CMAKE_CONFIGURE_ARGS+=	-DDESKTOP_APP_CPPGIR_DATA_DIR=${TOOLBASE}/share/cppgir
CMAKE_CONFIGURE_ARGS+=	-DDESKTOP_APP_GIR_DIR=${CROSS_DESTDIR:U}${LOCALBASE}/share/gir-1.0
TOOL_DEPENDS+=	cppgir>=2.0.0nb2:../../devel/cppgir
TOOL_DEPENDS+=	gobject-introspection>=1.86.0nb4:../../devel/gobject-introspection
TOOL_DEPENDS+=	zxcvbn-c>=2.7nb2:../../security/zxcvbn-c
CMAKE_CONFIGURE_ARGS+=	-DZXCVBN_NATIVE_DICTGEN=${TOOLBASE}/bin/zxcvbn-dictgen
CMAKE_CONFIGURE_ARGS+=	-DZXCVBN_WORDS_DIR=${TOOLBASE}/share/zxcvbn
TOOL_DEPENDS+=	qt6-qtshadertools-[0-9]*:../../graphics/qt6-qtshadertools
CMAKE_CONFIGURE_ARGS+=	-DQSB_EXECUTABLE=${TOOLBASE}/qt6/bin/qsb
TOOL_DEPENDS+=	telegram-desktop-codegen=${TDESKTOP_VERSION}nb${TDESKTOP_CODEGEN_REVISION}:../../chat/telegram-desktop-codegen
CMAKE_CONFIGURE_ARGS+=	-DTDESKTOP_NATIVE_CODEGEN_DIR=${TOOLBASE}/libexec/telegram-desktop-codegen
.include "../../mk/bsd.prefs.mk"

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
EMBERBSD_GI_MESON_OPTIONS= no
.include "../../devel/gobject-introspection/cross.mk"
CMAKE_CONFIGURE_ARGS+= -DDESKTOP_APP_GIRSCANNER=${WRKDIR}/.meson-gi-scanner
MAKE_ENV+= GI_GIR_PATH=${CROSS_DESTDIR}${LOCALBASE}/share/gir-1.0
.else
CMAKE_CONFIGURE_ARGS+= -DDESKTOP_APP_GIRSCANNER=${TOOLBASE}/bin/g-ir-scanner
.endif

# Upstream uses LINUX as its Unix desktop source selector (also used by BSD
# ports); the actual CMake target remains NetBSD and WebRTC is selected natively.
.if ${OPSYS} == "NetBSD"
CMAKE_CONFIGURE_ARGS+=	-DLINUX=ON
.endif

# Credentials are configured externally; the upstream test identity is never
# enabled implicitly and is unsuitable for deployed packages.
.if defined(TELEGRAM_API_ID) && defined(TELEGRAM_API_HASH)
CMAKE_CONFIGURE_ARGS+=	-DTDESKTOP_API_ID=${TELEGRAM_API_ID:Q}
CMAKE_CONFIGURE_ARGS+=	-DTDESKTOP_API_HASH=${TELEGRAM_API_HASH:Q}
.endif
.if defined(TELEGRAM_API_TEST) && ${TELEGRAM_API_TEST} == "yes"
CMAKE_CONFIGURE_ARGS+=	-DTDESKTOP_API_TEST=ON
# Upstream test credentials are restricted to local configure/build diagnostics.
pre-install pre-package:
	${ERROR_MSG} "TELEGRAM_API_TEST is for local diagnostics only"; ${FALSE}
.endif

.include "../../devel/cmake/build.mk"
.include "../../archivers/lz4/buildlink3.mk"
.include "../../archivers/minizip-ng/buildlink3.mk"
.include "../../devel/ada-url/buildlink3.mk"
.include "../../devel/boost-libs/buildlink3.mk"
.include "../../devel/cppgir/buildlink3.mk"
.include "../../devel/glib2/buildlink3.mk"
.include "../../devel/kf6-kcoreaddons/buildlink3.mk"
.include "../../devel/pango/buildlink3.mk"
.include "../../devel/microsoft-gsl/buildlink3.mk"
.include "../../devel/range-v3/buildlink3.mk"
.include "../../devel/tl-expected/buildlink3.mk"
.include "../../devel/toomanycooks/buildlink3.mk"
.include "../../devel/tdesktop-rust/buildlink3.mk"
.include "../../net/tde2e/buildlink3.mk"
.include "../../net/tg_owt/buildlink3.mk"
.include "../../devel/xxhash/buildlink3.mk"
.include "../../graphics/microtex/buildlink3.mk"
.include "../../graphics/qr-code-generator/buildlink3.mk"
.include "../../graphics/qt6-qtsvg/buildlink3.mk"
.include "../../multimedia/ffmpeg9/buildlink3.mk"
.include "../../multimedia/libvpx/buildlink3.mk"
.include "../../multimedia/libyuv/buildlink3.mk"
.include "../../multimedia/openh264/buildlink3.mk"
.include "../../audio/libopus/buildlink3.mk"
.include "../../audio/openal-soft/buildlink3.mk"
.include "../../audio/rnnoise/buildlink3.mk"
.include "../../security/libfido2/buildlink3.mk"
.include "../../security/zxcvbn-c/buildlink3.mk"
.include "../../security/openssl/buildlink3.mk"
.include "../../textproc/cmark-gfm/buildlink3.mk"
.include "../../textproc/cld3/buildlink3.mk"
.include "../../textproc/hunspell/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

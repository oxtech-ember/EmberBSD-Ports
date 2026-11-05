# Native source generators for Telegram Desktop.
.include "../telegram-desktop/Makefile.common"
PKGNAME= telegram-desktop-codegen-${TDESKTOP_VERSION}
PKGREVISION= ${TDESKTOP_CODEGEN_REVISION}
HOMEPAGE= https://desktop.telegram.org/
COMMENT= Native source generators for Telegram Desktop
LICENSE= gnu-gpl-v3
USE_LANGUAGES= c c++
USE_CXX_FEATURES+= c++20
USE_TOOLS+= pkg-config
CMAKE_CONFIGURE_ARGS+= -DTDESKTOP_CODEGEN_ONLY=ON
CMAKE_CONFIGURE_ARGS+= -DDESKTOP_APP_USE_PACKAGED=ON
CMAKE_CONFIGURE_ARGS+= -DDESKTOP_APP_DISABLE_QT_PLUGINS=ON
.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
PKG_FAIL_REASON+= "Telegram source generators require a native compiler"
.endif
.if ${OPSYS} == "Darwin"
CMAKE_CONFIGURE_ARGS+= -DCMAKE_OBJC_COMPILER=${WRAPPER_CC}
CMAKE_CONFIGURE_ARGS+= -DCMAKE_OBJCXX_COMPILER=${WRAPPER_CXX}
.endif
.if ${OPSYS} == "Linux" || ${OPSYS} == "NetBSD" || ${OPSYS} == "FreeBSD" || ${OPSYS} == "OpenBSD" || ${OPSYS} == "DragonFly"
.include "../../devel/cppgir/buildlink3.mk"
.include "../../devel/kf6-kcoreaddons/buildlink3.mk"
.include "../../devel/glib2/buildlink3.mk"
CMAKE_CONFIGURE_ARGS+= -DDESKTOP_APP_CPPGIR_EXECUTABLE=${TOOLBASE}/bin/cppgir
CMAKE_CONFIGURE_ARGS+= -DDESKTOP_APP_CPPGIR_DATA_DIR=${TOOLBASE}/share/cppgir
CMAKE_CONFIGURE_ARGS+= -DDESKTOP_APP_GIR_DIR=${LOCALBASE}/share/gir-1.0
.endif
INSTALLATION_DIRS+= share/licenses/telegram-desktop-codegen
post-install:
	${INSTALL_DATA} ${WRKSRC}/LICENSE ${WRKSRC}/LEGAL ${DESTDIR}${PREFIX}/share/licenses/telegram-desktop-codegen/
	${INSTALL_DATA} ${FILESDIR}/LEGAL-desktop-app ${DESTDIR}${PREFIX}/share/licenses/telegram-desktop-codegen/

.include "../../devel/cmake/build.mk"
.include "../../devel/microsoft-gsl/buildlink3.mk"
.include "../../devel/range-v3/buildlink3.mk"
.include "../../devel/tl-expected/buildlink3.mk"
.include "../../devel/xxhash/buildlink3.mk"
.include "../../security/openssl/buildlink3.mk"
.include "../../graphics/qt6-qtsvg/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

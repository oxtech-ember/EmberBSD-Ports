# $NetBSD$
# Packaged providers and native BSD camera integration.
DISTNAME= tg_owt-020feec5c040fdae2cf752c2c2be62ddde7c236d
PKGNAME= tg_owt-0.0.20261030
PKGREVISION= 2
CATEGORIES= net
MASTER_SITES= -https://github.com/desktop-app/tg_owt/archive/020feec5c040fdae2cf752c2c2be62ddde7c236d.tar.gz
HOMEPAGE= https://github.com/desktop-app/tg_owt/
COMMENT= WebRTC library used by Telegram Desktop
LICENSE= modified-bsd AND tg-owt-third-party
USE_LANGUAGES= c c++
USE_TOOLS+= pkg-config
CMAKE_CONFIGURE_ARGS+= -DBUILD_SHARED_LIBS=ON
CMAKE_CONFIGURE_ARGS+= -DTG_OWT_PACKAGED_BUILD=ON
CMAKE_CONFIGURE_ARGS+= -DTG_OWT_USE_X11=ON
CMAKE_CONFIGURE_ARGS+= -DTG_OWT_USE_PIPEWIRE=ON
INSTALLATION_DIRS+= share/licenses/tg_owt
post-install:
	${INSTALL_DATA} ${WRKSRC}/LICENSE ${WRKSRC}/src/AUTHORS ${WRKSRC}/src/PATENTS ${DESTDIR}${PREFIX}/share/licenses/tg_owt/
	${INSTALL_DATA} ${WRKSRC}/src/third_party/rnnoise/COPYING ${WRKSRC}/src/third_party/rnnoise/README.chromium ${DESTDIR}${PREFIX}/share/licenses/tg_owt/
	${INSTALL_DATA_DIR} ${DESTDIR}${PREFIX}/share/licenses/tg_owt/common_audio/third_party/ooura
	${INSTALL_DATA} ${WRKSRC}/src/common_audio/third_party/ooura/LICENSE ${WRKSRC}/src/common_audio/third_party/ooura/README.chromium ${DESTDIR}${PREFIX}/share/licenses/tg_owt/common_audio/third_party/ooura/
	${INSTALL_DATA_DIR} ${DESTDIR}${PREFIX}/share/licenses/tg_owt/modules/third_party/g711
	${INSTALL_DATA} ${WRKSRC}/src/modules/third_party/g711/LICENSE ${WRKSRC}/src/modules/third_party/g711/README.chromium ${DESTDIR}${PREFIX}/share/licenses/tg_owt/modules/third_party/g711/
	${INSTALL_DATA_DIR} ${DESTDIR}${PREFIX}/share/licenses/tg_owt/modules/third_party/g722
	${INSTALL_DATA} ${WRKSRC}/src/modules/third_party/g722/LICENSE ${WRKSRC}/src/modules/third_party/g722/README.chromium ${DESTDIR}${PREFIX}/share/licenses/tg_owt/modules/third_party/g722/
	${INSTALL_DATA_DIR} ${DESTDIR}${PREFIX}/share/licenses/tg_owt/modules/third_party/portaudio
	${INSTALL_DATA} ${WRKSRC}/src/modules/third_party/portaudio/LICENSE ${WRKSRC}/src/modules/third_party/portaudio/README.chromium ${DESTDIR}${PREFIX}/share/licenses/tg_owt/modules/third_party/portaudio/
	${INSTALL_DATA_DIR} ${DESTDIR}${PREFIX}/share/licenses/tg_owt/rtc_base/third_party/base64
	${INSTALL_DATA} ${WRKSRC}/src/rtc_base/third_party/base64/LICENSE ${WRKSRC}/src/rtc_base/third_party/base64/README.chromium ${DESTDIR}${PREFIX}/share/licenses/tg_owt/rtc_base/third_party/base64/
	${INSTALL_DATA_DIR} ${DESTDIR}${PREFIX}/share/licenses/tg_owt/rtc_base/third_party/sigslot
	${INSTALL_DATA} ${WRKSRC}/src/rtc_base/third_party/sigslot/LICENSE ${WRKSRC}/src/rtc_base/third_party/sigslot/README.chromium ${DESTDIR}${PREFIX}/share/licenses/tg_owt/rtc_base/third_party/sigslot/

.include "../../audio/libopus/buildlink3.mk"
.include "../../audio/pffft/buildlink3.mk"
.include "../../devel/abseil/buildlink3.mk"
.include "../../multimedia/ffmpeg9/buildlink3.mk"
.include "../../multimedia/libvpx/buildlink3.mk"
.include "../../multimedia/openh264/buildlink3.mk"
.include "../../multimedia/pipewire/buildlink3.mk"
.include "../../devel/crc32c/buildlink3.mk"
.include "../../security/libsrtp/buildlink3.mk"
.include "../../multimedia/libyuv/buildlink3.mk"
.include "../../devel/glib2/buildlink3.mk"
.include "../../mk/jpeg.buildlink3.mk"
.include "../../graphics/MesaLib/buildlink3.mk"
.include "../../x11/libX11/buildlink3.mk"
.include "../../x11/libXcomposite/buildlink3.mk"
.include "../../x11/libXdamage/buildlink3.mk"
.include "../../x11/libXext/buildlink3.mk"
.include "../../x11/libXfixes/buildlink3.mk"
.include "../../x11/libXrandr/buildlink3.mk"
.include "../../x11/libXrender/buildlink3.mk"
.include "../../x11/libXtst/buildlink3.mk"
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"

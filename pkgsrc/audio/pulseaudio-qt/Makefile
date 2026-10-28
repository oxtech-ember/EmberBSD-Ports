# Origin: EmberBSD (AI-assisted).

DISTNAME= pulseaudio-qt-1.9.0
CATEGORIES= audio kde
MASTER_SITES= ${MASTER_SITE_KDE:=pulseaudio-qt/}
EXTRACT_SUFX= .tar.xz

HOMEPAGE= https://invent.kde.org/libraries/pulseaudio-qt
COMMENT= Qt 6 bindings for the PulseAudio client API
LICENSE= gnu-lgpl-v2.1 OR gnu-lgpl-v3

.include "../../meta-pkgs/kde/applications.mk"

USE_TOOLS+= pkg-config
CMAKE_CONFIGURE_ARGS+= -DBUILD_TESTING=ON
CMAKE_CONFIGURE_ARGS+= -DCMAKE_EXPORT_COMPILE_COMMANDS=ON

.include "../../audio/pulseaudio/buildlink3.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

# Origin: EmberBSD (AI-assisted).

DISTNAME= plasma-pa-${PLASMAVER}
CATEGORIES= audio

HOMEPAGE= https://invent.kde.org/plasma/plasma-pa
COMMENT= PulseAudio volume controls for KDE Plasma 6
LICENSE= gnu-gpl-v2 AND gnu-lgpl-v2.1

.include "../../meta-pkgs/kde/plasma6.mk"

USE_TOOLS+= msgmerge pkg-config
CMAKE_CONFIGURE_ARGS+= -DBUILD_TESTING=ON
CMAKE_CONFIGURE_ARGS+= -DCMAKE_EXPORT_COMPILE_COMMANDS=ON

# The KCM and applet import these QML modules at runtime.
DEPENDS+= kf6-kirigami>=6.31.0:../../x11/kf6-kirigami
DEPENDS+= kirigami-addons>=1.10.0:../../x11/kirigami-addons
DEPENDS+= kf6-kitemmodels>=6.31.0:../../devel/kf6-kitemmodels

.include "../../audio/libcanberra/buildlink3.mk"
.include "../../audio/pulseaudio/buildlink3.mk"
.include "../../audio/pulseaudio-qt/buildlink3.mk"
.include "../../devel/glib2/buildlink3.mk"
.include "../../devel/kf6-kcmutils/buildlink3.mk"
.include "../../devel/kf6-kconfig/buildlink3.mk"
.include "../../devel/kf6-kcoreaddons/buildlink3.mk"
.include "../../devel/kf6-kdeclarative/buildlink3.mk"
.include "../../devel/kf6-ki18n/buildlink3.mk"
.include "../../graphics/kf6-ksvg/buildlink3.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../misc/kf6-kstatusnotifieritem/buildlink3.mk"
.include "../../sysutils/kf6-kdbusaddons/buildlink3.mk"
.include "../../devel/kf6-kdoctools/tools.mk"
.include "../../x11/kf6-kglobalaccel/buildlink3.mk"
.include "../../x11/plasma6-libplasma/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

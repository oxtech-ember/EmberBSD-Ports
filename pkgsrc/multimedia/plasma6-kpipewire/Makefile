# $NetBSD$

DISTNAME=	kpipewire-${PLASMAVER}
CATEGORIES=	multimedia

HOMEPAGE=	https://invent.kde.org/plasma/kpipewire
COMMENT=	KDE PipeWire stream integration
LICENSE=	gnu-lgpl-v2.1 AND gnu-lgpl-v3 AND modified-bsd

.include "../../meta-pkgs/kde/plasma6.mk"

USE_TOOLS+=	pkg-config

.include "../../devel/kf6-kcoreaddons/buildlink3.mk"
.include "../../devel/kf6-ki18n/buildlink3.mk"
.include "../../graphics/MesaLib/buildlink3.mk"
.include "../../graphics/libepoxy/buildlink3.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../multimedia/ffmpeg9/buildlink3.mk"
.include "../../multimedia/libva/buildlink3.mk"
.include "../../multimedia/pipewire/buildlink3.mk"
.include "../../x11/libdrm/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

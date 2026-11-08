# $NetBSD$

DISTNAME=	ksystemstats-${PLASMAVER}
CATEGORIES=	sysutils

HOMEPAGE=	https://kde.org/plasma-desktop/
COMMENT=	Plugin based system monitoring daemon
LICENSE=	gnu-lgpl-v2.1 AND gnu-gpl-v2 AND gnu-gpl-v3

.include "../../meta-pkgs/kde/plasma6.mk"

# CPU, memory and network plugins have Linux and FreeBSD backends only.
# The package still builds the common plugins. Those three stay without a
# NetBSD data source.

USE_TOOLS+=	msgmerge pkg-config

.include "../../devel/kf6-kcoreaddons/buildlink3.mk"
.include "../../devel/kf6-kcrash/buildlink3.mk"
.include "../../devel/kf6-ki18n/buildlink3.mk"
.include "../../devel/kf6-kio/buildlink3.mk"
.include "../../devel/libudev-bsd/buildlink3.mk"
.include "../../sysutils/kf6-solid/buildlink3.mk"
.include "../../sysutils/plasma6-libksysguard/buildlink3.mk"
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

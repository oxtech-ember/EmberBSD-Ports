# $NetBSD$

DISTNAME=	ksystemstats-${PLASMAVER}
PKGREVISION=	3
CATEGORIES=	sysutils

HOMEPAGE=	https://kde.org/plasma-desktop/
COMMENT=	Plugin based system monitoring daemon
LICENSE=	gnu-lgpl-v2.1 AND gnu-gpl-v2 AND gnu-gpl-v3

.include "../../meta-pkgs/kde/plasma6.mk"

# NetBSD reads kern.cp_time, vm.uvmexp2 and getifaddrs. There is no iowait
# counter and no per-core frequency or temperature node.

USE_TOOLS+=	msgmerge pkg-config

post-extract:
	${CP} ${FILESDIR}/netbsdcpuplugin.h ${WRKSRC}/plugins/cpu/netbsdcpuplugin.h
	${CP} ${FILESDIR}/netbsdcpuplugin.cpp ${WRKSRC}/plugins/cpu/netbsdcpuplugin.cpp
	${CP} ${FILESDIR}/memory/netbsdbackend.h ${WRKSRC}/plugins/memory/netbsdbackend.h
	${CP} ${FILESDIR}/memory/netbsdbackend.cpp ${WRKSRC}/plugins/memory/netbsdbackend.cpp
	${CP} ${FILESDIR}/network/NetBsdBackend.h ${WRKSRC}/plugins/network/NetBsdBackend.h
	${CP} ${FILESDIR}/network/NetBsdBackend.cpp ${WRKSRC}/plugins/network/NetBsdBackend.cpp

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

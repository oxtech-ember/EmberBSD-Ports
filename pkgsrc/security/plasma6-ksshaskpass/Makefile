# $NetBSD: Makefile,v 1.8 2026/09/06 10:23:30 markd Exp $

DISTNAME=	ksshaskpass-${PLASMAVER}
PKGREVISION=	1
CATEGORIES=	security

HOMEPAGE=	https://kde.org/plasma-desktop/
COMMENT=	ssh-add helper that uses kwallet and kpassworddialog
LICENSE=	gnu-gpl-v2

.include "../../meta-pkgs/kde/plasma6.mk"

USE_TOOLS+=	msgmerge

# The manual page needs KDocTools, which CMake finds only when it is present.
.include "../../devel/kf6-kdoctools/tools.mk"

.include "../../security/kf6-kwallet/buildlink3.mk"
.include "../../security/qt6-qtkeychain/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

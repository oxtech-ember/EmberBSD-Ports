# $NetBSD: Makefile,v 1.8 2026/09/06 10:23:30 markd Exp $

DISTNAME=	ksshaskpass-${PLASMAVER}
CATEGORIES=	security

HOMEPAGE=	https://kde.org/plasma-desktop/
COMMENT=	ssh-add helper that uses kwallet and kpassworddialog
LICENSE=	gnu-gpl-v2

.include "../../meta-pkgs/kde/plasma6.mk"

# kf6-kdoctools-generators is already installed and conflicts with the full package.
USE_TOOLS+=	msgmerge

.include "../../security/kf6-kwallet/buildlink3.mk"
.include "../../security/qt6-qtkeychain/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

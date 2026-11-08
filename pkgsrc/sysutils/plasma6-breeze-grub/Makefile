# $NetBSD$

DISTNAME=	breeze-grub-6.8.2
PKGNAME=	plasma6-${DISTNAME}
CATEGORIES=	sysutils
MASTER_SITES=	https://download.kde.org/stable/plasma/6.8.2/
EXTRACT_SUFX=	.tar.xz

HOMEPAGE=	https://kde.org/plasma-desktop/
COMMENT=	Breeze theme data for GRUB
LICENSE=	gnu-gpl-v2 AND gnu-gpl-v3 AND cc-by-sa-v4.0

# Theme files only. They are installed under share/examples so a bootloader
# does not load them. The boot configuration is not changed.

NO_CONFIGURE=	yes
NO_BUILD=	yes

do-install:
	${INSTALL_DATA_DIR} ${DESTDIR}${PREFIX}/share/examples/plasma6-breeze-grub/breeze
	${INSTALL_DATA} ${WRKSRC}/breeze/* \
		${DESTDIR}${PREFIX}/share/examples/plasma6-breeze-grub/breeze/

.include "../../mk/bsd.pkg.mk"

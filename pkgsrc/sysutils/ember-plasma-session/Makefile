# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Package the canonical ordinary-user service.
DISTNAME=	ember-plasma-session-1.0
PKGREVISION=	1
CATEGORIES=	sysutils
MASTER_SITES=
DISTFILES=

MAINTAINER=	oxtech-ember@users.noreply.github.com
HOMEPAGE=	https://github.com/oxtech-ember/EmberBSD-Ports
COMMENT=	Opt-in persistent ordinary-user Plasma session
LICENSE=	2-clause-bsd

NO_CONFIGURE=	yes
NO_BUILD=	yes
USE_LANGUAGES=	# none
ONLY_FOR_PLATFORM=	NetBSD-*-*

DEPENDS+=	plasma6-plasma-desktop>=6.8.2:../../x11/plasma6-plasma-desktop
DEPENDS+=	plasma6-plasma-workspace>=6.8.2nb3:../../x11/plasma6-plasma-workspace
DEPENDS+=	plasma6-kwin>=6.8.2nb2:../../x11/plasma6-kwin
DEPENDS+=	qt6-qtbase>=6.12.0nb3:../../x11/qt6-qtbase
DEPENDS+=	perl>=5.44.0:../../lang/perl5
DEPENDS+=	dbus>=1.16.2:../../sysutils/dbus
DEPENDS+=	xwayland>=24.1.14nb3:../../wayland/xwayland

RCD_SCRIPTS=	ember_plasma
RCD_SCRIPT_SRC.ember_plasma=	${FILESDIR}/ember_plasma.rc
INSTALLATION_DIRS=	libexec

.include "../../mk/bsd.prefs.mk"
.if ${PREFIX:U/usr/pkg} != "/usr/pkg"
PKG_FAIL_REASON+= "The canonical Plasma service requires PREFIX=/usr/pkg"
.endif

do-install:
	${INSTALL_SCRIPT} ${FILESDIR}/plasma-service.pl ${DESTDIR}${PREFIX}/libexec/ember-plasma-service

.include "../../mk/bsd.pkg.mk"

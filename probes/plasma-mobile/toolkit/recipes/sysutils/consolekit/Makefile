# $NetBSD: Makefile,v 1.58 2026/09/02 19:04:25 wiz Exp $

CONSOLEKIT_VER=	2.0.0
DISTNAME=	ConsoleKit2-${CONSOLEKIT_VER}
PKGNAME=	consolekit-${CONSOLEKIT_VER}
PKGREVISION=	4
CATEGORIES=	sysutils
GITHUB_TAG=	${CONSOLEKIT_VER}
GITHUB_PROJECT=	ConsoleKit2
MASTER_SITES=	${MASTER_SITE_GITHUB:=ConsoleKit2/}

MAINTAINER=	youri@NetBSD.org
HOMEPAGE=	https://github.com/ConsoleKit2/ConsoleKit2
COMMENT=	Framework for defining and tracking users, login sessions, and seats
LICENSE=	gnu-gpl-v2

MESSAGE_SUBST+=	PREFIX=${PREFIX}

BUILD_DEFS+=	VARBASE \
		PKG_SYSCONFBASE

EGDIR=			${PREFIX}/share/examples/consolekit
PKG_SYSCONFSUBDIR=	ConsoleKit
RULESDIR=		${PREFIX}/share/polkit-1/rules.d

MAKE_DIRS=	${PKG_SYSCONFDIR}/run-seat.d		\
		${PKG_SYSCONFDIR}/run-session.d		\
		${PKG_SYSCONFDIR}/seats.d		\
		${PKG_SYSCONFBASE}/dbus-1/system.d	\
		${PKG_SYSCONFBASE}/logrotate.d		\
		${PKG_SYSCONFBASE}/X11/xinit/xinitrc.d


CONF_FILES+=	${EGDIR}/ConsoleKit/seats.d/00-primary.seat		\
		${PKG_SYSCONFDIR}/seats.d/00-primary.seat		\
		${EGDIR}/dbus-1/system.d/ConsoleKit.conf 		\
		${PKG_SYSCONFBASE}/dbus-1/system.d/ConsoleKit.conf 	\
		${EGDIR}/logrotate.d/consolekit				\
		${PKG_SYSCONFBASE}/logrotate.d/consolekit		\
		${EGDIR}/X11/xinit/xinitrc.d/90-consolekit		\
		${PKG_SYSCONFBASE}/X11/xinit/xinitrc.d/90-consolekit

GNU_CONFIGURE=	YES
USE_TOOLS+=	gmake msgfmt perl pkg-config
USE_TOOLS+=	autoconf automake autoreconf autopoint
USE_TOOLS+=	gdbus-codegen
USE_LIBTOOL=	YES

CONFIGURE_ARGS+=	--sysconfdir=${PKG_SYSCONFBASE}			\
			--localstatedir=${VARBASE}			\
			--disable-pam-module
		#--enable-pam-module
		#--with-pam-module-dir=${PREFIX}/lib/security

# Keep the shipped X11 helper programs; upstream 2.0 requires explicit selection.
CONFIGURE_ARGS+=	--with-x --enable-tests

CONFIGURE_ARGS.SunOS+=	--enable-rbac-shutdown=solaris.system.shutdown

INSTALL_MAKE_FLAGS+=	sysconfdir=${EGDIR} 			\
			DBUS_SYS_DIR=${EGDIR}/dbus-1/system.d	\
			XINITRC_DIR=${EGDIR}/X11/xinit/xinitrc.d

post-install:
	${MKDIR} ${DESTDIR}${RULESDIR} &&		\
	${INSTALL_DATA} ${FILESDIR}/50-shutdown.rules	\
	${DESTDIR}${RULESDIR}/50-shutdown.rules

pre-configure:
	cd ${WRKSRC} && NOCONFIGURE=1 ${SH} autogen.sh

.include "../../devel/zlib/buildlink3.mk"
# ConsoleKit 2.0 uses short session IDs; keep its policy consumer compatible.
BUILDLINK_API_DEPENDS.polkit+=	polkit>=127nb4
.include "../../security/polkit/buildlink3.mk"
.include "../../sysutils/dbus/buildlink3.mk"
.include "../../devel/glib2/buildlink3.mk"
.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# Upstream's autogen supports absent gtk-doc; default API HTML stays disabled.
# Shipped manual pages and every default runtime component remain installed.
CONFIGURE_ENV+= ac_cv_file__sys_class_tty_tty0_active=no
CONFIGURE_ENV+= GLIB_GENMARSHAL=${TOOLBASE}/bin/glib-genmarshal
CONFIGURE_ENV+= GDBUS_CODEGEN=${TOOLBASE}/bin/gdbus-codegen
.else
.include "../../textproc/gtk-doc/buildlink3.mk"
.endif
.include "../../x11/libX11/buildlink3.mk"
.include "../../mk/pam.buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

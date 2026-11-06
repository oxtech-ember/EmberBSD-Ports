# $NetBSD: Makefile,v 1.146 2026/09/02 19:04:25 wiz Exp $

DISTNAME=	dbus-1.16.2
PKGREVISION=	13
CATEGORIES=	sysutils
MASTER_SITES=	https://dbus.freedesktop.org/releases/dbus/
EXTRACT_SUFX=	.tar.xz

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://www.freedesktop.org/Software/dbus
COMMENT=	Message bus system
LICENSE=	gnu-gpl-v2

TOOL_DEPENDS+=	xmlto-[0-9]*:../../textproc/xmlto

CONFLICTS+=	dbus-glib<0.71
CONFLICTS+=	py27-dbus<0.71

USE_TOOLS+=		msgfmt pkg-config
USE_CC_FEATURES=	c99

PKGCONFIG_OVERRIDE+=		output/meson-private/dbus-1.pc
PKGCONFIG_OVERRIDE_STAGE=	post-configure

BUILD_DEFS+=		VARBASE PKG_SYSCONFBASE

CHECK_PORTABILITY_SKIP+=	tools/cmake-format

.include "../../mk/bsd.prefs.mk"

# Keep Meson's build-tree DSO path for uninstalled Darwin tests.
# Origin: EmberBSD (AI-assisted); use the pkgsrc buildlink passthrough API.
.if ${OPSYS} == "Darwin"
BUILDLINK_PASSTHRU_RPATHDIRS+=	@loader_path/../dbus
.endif

# Select the build-host XSLT processor and XML catalog for DocBook probes.
# Meson's xsltproc --nonet check needs a resolvable catalog; without it,
# html/manpages are disabled while PLIST still requires them (native and cross).
# Origin: EmberBSD (AI-assisted).
TOOL_DEPENDS+=		docbook-xsl-[0-9]*:../../textproc/docbook-xsl
MESON_BINARIES+=		xsltproc
MESON_BINARY.xsltproc=	${TOOLBASE}/bin/xsltproc
MESON_ARGS+=		-Dxml_docs=enabled
MAKE_ENV+=		XML_CATALOG_FILES=${TOOLBASE}/etc/xml/catalog
CONFIGURE_ENV+=		XML_CATALOG_FILES=${TOOLBASE}/etc/xml/catalog
.if ${USE_CROSS_COMPILE:U:tl} == "yes"
# Runtime sockets belong to the target, never the build host's TMPDIR.
MESON_ARGS+=		-Dsession_socket_dir=/tmp -Dtest_socket_dir=/tmp

post-configure: emberbsd-dbus-runtime-paths
.PHONY: emberbsd-dbus-runtime-paths
emberbsd-dbus-runtime-paths:
	${RUN} ${GREP} -Fxq '#define DBUS_SESSION_SOCKET_DIR "/tmp"' ${WRKSRC}/output/config.h
	${RUN} ${GREP} -Fxq '#define DBUS_TEST_SOCKET_DIR "/tmp"' ${WRKSRC}/output/config.h
	${RUN} ${GREP} -Fxq '#define TEST_LISTEN "unix:tmpdir=/tmp"' ${WRKSRC}/output/config.h
	${RUN} ${GREP} -Fq '<listen>unix:tmpdir=/tmp</listen>' ${WRKSRC}/output/bus/session.conf
.endif


MESON_ARGS+=		-Ddbus_user=${DBUS_USER}
MESON_ARGS+=		-Dlocalstatedir=${VARBASE}
MESON_ARGS+=		-Dsystem_socket=${VARBASE}/run/dbus/system_bus_socket
MESON_ARGS+=		-Dsystem_pid_file=${VARBASE}/run/dbus/pid
MESON_ARGS+=		-Ddoxygen_docs=disabled

LDFLAGS.SunOS+=		-lsocket -lnsl

SUBST_CLASSES+=		docbook
SUBST_STAGE.docbook=	pre-configure
SUBST_FILES.docbook=	doc/*.xml*
SUBST_SED.docbook=	-e 's,http://www.oasis-open.org/docbook/xml,${PREFIX}/share/xml/docbook,g'

.if ${OPSYS} == "SunOS"
MESON_ARGS+=		-Dinotify=disabled
MESON_ARGS+=		-Dsolaris_console_owner_file="/dev/vt/console_user"
.endif

DBUS_CONF_DIR=		${PKG_SYSCONFBASE}/dbus-1
OWN_DIRS+=		${DBUS_CONF_DIR}/services
OWN_DIRS+=		${DBUS_CONF_DIR}/session.d

BUILDLINK_TRANSFORM.FreeBSD+=	rm:-Wl,--no-undefined
BUILDLINK_TRANSFORM+=		rm:-Wl,--gc-sections
.if !empty(_PKGSRC_MKPIE:M[Nn][Oo])
# Package tries to use these if gcc accepts them, but that doesn't
# mean that we universally can *run* the executables
BUILDLINK_TRANSFORM+=		rm:-fPIE
BUILDLINK_TRANSFORM+=		rm:-pie
.endif

.include "options.mk"

.if !empty(PKG_OPTIONS:Mdbus-system)
OWN_DIRS_PERMS+=	${VARBASE}/lib/dbus ${DBUS_USER} ${DBUS_GROUP} 0755
SPECIAL_PERMS+=		libexec/dbus-daemon-launch-helper ${REAL_ROOT_USER} ${DBUS_GROUP} 4511
SMF_METHODS=		dbus
SMF_NAME=		dbus
OWN_DIRS+=		${DBUS_CONF_DIR}/system-services
OWN_DIRS+=		${DBUS_CONF_DIR}/system.d
RCD_SCRIPTS=		dbus
PKG_GROUPS_VARS+=	DBUS_GROUP
PKG_USERS_VARS+=	DBUS_USER
PKG_GROUPS=		${DBUS_GROUP}
PKG_USERS=		${DBUS_USER}:${DBUS_GROUP}
PKG_GECOS.${DBUS_USER}=	System message bus
PKG_HOME.${DBUS_USER}=	${VARBASE}/run/dbus
FILES_SUBST+=		DBUS_USER=${DBUS_USER}
FILES_SUBST+=		DBUS_GROUP=${DBUS_GROUP}
.else
# Session tools still require a prefix-owned machine-id directory.
OWN_DIRS+=		${VARBASE}/lib/dbus
.endif

post-install:
.if empty(PKG_OPTIONS:Mdbus-system)
	${RM} -f ${DESTDIR}${PREFIX}/libexec/dbus-daemon-launch-helper
	${RM} -f ${DESTDIR}${PREFIX}/share/dbus-1/system.conf
.endif
	${INSTALL_DATA} ${WRKSRC}/doc/introspect.* \
		${DESTDIR}${PREFIX}/share/doc/dbus/
	${RM} -f ${DESTDIR}${PREFIX}/etc/dbus-1/s*.conf
	${RMDIR} ${DESTDIR}${PREFIX}/etc/dbus-1 || ${TRUE}

.include "../../devel/meson/build.mk"
.include "../../lang/python/tool.mk"
.include "../../mk/pthread.buildlink3.mk"
.include "../../devel/gettext-lib/buildlink3.mk"
BUILDLINK_API_DEPENDS.expat+=	expat>=2.1.0
.include "../../textproc/expat/buildlink3.mk"
.include "../../devel/glib2/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

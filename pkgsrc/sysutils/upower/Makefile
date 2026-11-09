# $NetBSD: Makefile,v 1.34 2026/09/02 19:04:38 wiz Exp $

DISTNAME=	upower-v1.91.2
PKGNAME=	${DISTNAME:S/v//}
PKGREVISION=	4
CATEGORIES=	sysutils
MASTER_SITES=	https://gitlab.freedesktop.org/upower/upower/-/archive/v${PKGVERSION_NOREV}/
EXTRACT_SUFX=	.tar.bz2

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://upower.freedesktop.org/
COMMENT=	Power management system message bus service
LICENSE=	gnu-gpl-v2

USE_CC_FEATURES=	c11
USE_TOOLS+=		pkg-config intltool gdbus-codegen \
			xgettext msgmerge msgfmt

USE_PKGLOCALEDIR=	yes

BUILD_DEFS+=	VARBASE PKG_SYSCONFBASE

TOOL_DEPENDS+=	docbook-xsl-[0-9]*:../../textproc/docbook-xsl

PKG_SYSCONFSUBDIR=	UPower
EGDIR=			${PREFIX}/share/examples/upower
CONF_FILES+=		${EGDIR}/UPower.conf ${PKG_SYSCONFDIR}/UPower.conf
CONF_FILES+=		${EGDIR}/org.freedesktop.UPower.conf \
			${PKG_SYSCONFBASE}/dbus-1/system.d/org.freedesktop.UPower.conf

.include "../../mk/bsd.prefs.mk"

# Free/OpenBSD and Linux are officially supported.
# EmberBSD adds a NetBSD backend on envsys(4) from files/netbsd.
.if ${OPSYS} == "OpenBSD" || ${OPSYS} == "FreeBSD" || ${OPSYS} =="Linux" || \
    ${OPSYS} == "NetBSD"
MESON_ARGS+=	-Dos_backend=${LOWER_OPSYS}
.else
MESON_ARGS+=	-Dos_backend=dummy
.endif

post-extract:
	${MKDIR} ${WRKSRC}/src/netbsd
	${CP} ${FILESDIR}/netbsd/* ${WRKSRC}/src/netbsd/

MESON_ARGS+=	--sysconfdir=${PKG_SYSCONFBASEDIR} \
		--localedir=${PKGLOCALEDIR}/locale \
		-Dstatedir=${VARBASE} \
		-Dhistorydir=${VARBASE}/db/upower \
		-Degdir=${EGDIR} \
		-Dzshcompletiondir=${PREFIX}/share/zsh/site-functions \
		-Dman=true \
		-Didevice=disabled

.if ${OPSYS} =="Linux"
.  include "../../lang/python/pyversion.mk"
.  include "../../lang/python/application.mk"

REPLACE_PYTHON=	integration-test.py unittest_inspector.py

.  include "../../devel/libgudev/buildlink3.mk"
MESON_ARGS+=	-Dudevrulesdir=${PREFIX}/lib/udev/rules.d \
		-Dudevhwdbdir=${PKG_SYSCONFBASEDIR}/udev/hwdb.d \
		-Dsystemdsystemunitdir=${EGDIR}
.else
MESON_ARGS+=    -Dudevrulesdir=disabled \
               	-Dudevhwdbdir=disabled \
               	-Dsystemdsystemunitdir=no
.endif

.include "options.mk"

# Select the build-host generators and XML catalog for DocBook man pages.
# Origin: EmberBSD (AI-assisted).
MESON_BINARIES+=	gdbus-codegen xsltproc
MESON_BINARY.gdbus-codegen=	${TOOLBASE}/bin/gdbus-codegen
MESON_BINARY.xsltproc=	${TOOLBASE}/bin/xsltproc
MAKE_ENV+=		XML_CATALOG_FILES=${TOOLBASE}/etc/xml/catalog
CONFIGURE_ENV+=		XML_CATALOG_FILES=${TOOLBASE}/etc/xml/catalog

BUILDLINK_TRANSFORM.Darwin+=	rm:-Wl,--as-needed
BUILDLINK_TRANSFORM.Darwin+=	rm:-Wl,--no-as-needed
BUILDLINK_TRANSFORM.SunOS+=	opt:-Wl,--no-as-needed:-Wl,-zrecord
BUILDLINK_TRANSFORM.SunOS+=	opt:-Wl,--as-needed:-Wl,-zignore

PKGCONFIG_OVERRIDE_STAGE=	pre-install
PKGCONFIG_OVERRIDE+=		output/meson-private/upower-glib.pc

# with --nonet, xsltproc needs a helping hand finding some dtds
XSLTPROC_PATH=	${PREFIX}/share/doc/dbus

.include "../../devel/gettext-tools/msgfmt-desktop.mk"
.include "../../devel/gettext-lib/buildlink3.mk"
BUILDLINK_API_DEPENDS.glib2+=   glib2>=2.66.0
.include "../../devel/glib2/buildlink3.mk"
.include "../../devel/zlib/buildlink3.mk"
# UPower 1.91 uses GDBus only; dbus-glib is not a dependency.
.include "../../sysutils/dbus/buildlink3.mk"
.include "../../textproc/libxslt/xsltproc-nonet.mk"
.include "../../devel/meson/build.mk"
.include "../../mk/bsd.pkg.mk"

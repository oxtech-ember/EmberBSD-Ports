# $NetBSD: Makefile,v 1.76 2026/09/02 19:01:23 wiz Exp $

DISTNAME=	dconf-51.0
CATEGORIES=	devel gnome
MASTER_SITES=	${MASTER_SITE_GNOME:=sources/dconf/${PKGVERSION_NOREV:R}/}
EXTRACT_SUFX=	.tar.xz

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://wiki.gnome.org/Projects/dconf
COMMENT=	Backend for gsettings
LICENSE=	gnu-lgpl-v2.1

TOOL_DEPENDS+=	libxslt-[0-9]*:../../textproc/libxslt
TOOL_DEPENDS+=	docbook-xsl-[0-9]*:../../textproc/docbook-xsl

USE_LANGUAGES=	c99
USE_TOOLS+=	pkg-config gdbus-codegen

PYTHON_FOR_BUILD_ONLY=	tool
REPLACE_PYTHON+=	*.py

MESON_ARGS+=		-D bash_completion=false
MESON_CROSS_VARS+=	gio_module_dir dbus_session_service_dir
MESON_CROSS.gio_module_dir=	'${GIO_MODULES_DIR}'
MESON_CROSS.dbus_session_service_dir=	'${PREFIX}/share/dbus-1/services'

PKGCONFIG_OVERRIDE=		output/meson-private/dconf.pc
PKGCONFIG_OVERRIDE_STAGE=	post-build

.include "../../mk/bsd.prefs.mk"

.include "../../devel/gvdb-source/build.mk"
BUILDLINK_API_DEPENDS.glib2+=	glib2>=2.76
#.include "../../textproc/gtk-doc/buildlink3.mk"
.include "../../devel/glib2/modules.mk"
.include "../../devel/meson/build.mk"
.include "../../sysutils/dbus/buildlink3.mk"
.include "../../lang/python/application.mk"
.include "../../mk/bsd.pkg.mk"

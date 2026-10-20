# $NetBSD: Makefile,v 1.41 2026/09/02 19:04:17 wiz Exp $

DISTNAME=	libsecret-0.20.5
PKGREVISION=	4
CATEGORIES=	security gnome
MASTER_SITES=	${MASTER_SITE_GNOME:=sources/libsecret/${PKGVERSION_NOREV:R}/}
EXTRACT_SUFX=	.tar.xz

MAINTAINER=	ryoon@NetBSD.org
HOMEPAGE=	https://wiki.gnome.org/Projects/Libsecret
COMMENT=	GObject based library for accessing the Secret Service API
LICENSE=	gnu-lgpl-v2.1

TOOL_DEPENDS+=	docbook-xsl-[0-9]*:../../textproc/docbook-xsl
.if ${USE_CROSS_COMPILE:Uno:tl} != "yes"
TOOL_DEPENDS+=	glib2-introspection-[0-9]*:../../devel/glib2-introspection
.endif
TOOL_DEPENDS+=	libxslt-[0-9]*:../../textproc/libxslt
TEST_DEPENDS+=	${PYPKGPREFIX}-dbus-[0-9]*:../../sysutils/py-dbus

USE_TOOLS+=	gdbus-codegen gsed pkg-config
USE_TOOLS+=	glib-mkenums
USE_TOOLS+=	msgfmt msgmerge xgettext

MESON_ARGS+=	-Dbash_completion=disabled

PKGCONFIG_OVERRIDE+=	libsecret/libsecret-unstable.pc.in
PKGCONFIG_OVERRIDE+=	libsecret/libsecret.pc.in

REPLACE_PYTHON=	libsecret/*.py
TEST_ENV+=	LD_LIBRARY_PATH=${WRKSRC}/output/libsecret
TEST_ENV+=	DYLD_LIBRARY_PATH=${WRKSRC}/output/libsecret

SUBST_CLASSES+=		python
SUBST_STAGE.python=	pre-configure
SUBST_MESSAGE.python=	Fixing Python executable path.
SUBST_FILES.python=	libsecret/mock-service.c
SUBST_SED.python=	-e 's,python3,${PYTHONBIN},'

BUILDLINK_API_DEPENDS.glib2+=	glib2>=2.44.0

.include "../../devel/glib2/buildlink3.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# The reference site is not needed by consumers and would require running
# target-side Graphviz through gi-docgen during the cross package build.
MESON_ARGS+=	-Dgtk_doc=false
MESON_ARGS+=	-Dvapi=false
MESON_ARGS+=	-Dintrospection=false
MESON_BINARIES+=	gdbus-codegen
MESON_BINARY.gdbus-codegen=	${TOOLS_CMD.gdbus-codegen}
MESON_BINARIES+=	glib-mkenums
MESON_BINARY.glib-mkenums=	${TOOLBASE}/bin/glib-mkenums
PLIST_SRC=	${.CURDIR}/PLIST.cross
.else
.include "../../devel/py-gi-docgen/buildlink3.mk"
.include "../../lang/vala/buildlink3.mk"
BUILDLINK_DEPMETHOD.gobject-introspection=	build
.include "../../devel/gobject-introspection/buildlink3.mk"
.endif
.include "../../devel/meson/build.mk"
.include "../../lang/python/application.mk"
.include "../../security/libgcrypt/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

# $NetBSD: Makefile,v 1.82 2026/09/02 19:02:36 wiz Exp $

DISTNAME=	gdk-pixbuf-2.44.8
PKGNAME=	${DISTNAME:S/pixbuf/pixbuf2/}
PKGREVISION=	4
CATEGORIES=	graphics gnome
MASTER_SITES=	${MASTER_SITE_GNOME:=sources/gdk-pixbuf/${PKGVERSION_NOREV:R}/}
EXTRACT_SUFX=	.tar.xz

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://gitlab.gnome.org/GNOME/gdk-pixbuf
COMMENT=	Library for image loading and manipulation
LICENSE=	gnu-gpl-v2

# for man pages
TOOL_DEPENDS+=	${PYPKGPREFIX}-docutils-[0-9]*:../../textproc/py-docutils

CONFLICTS+=	gtk2+<2.22

USE_TOOLS+=	pkg-config xgettext

SUBST_CLASSES+=		rst2man
SUBST_MESSAGE.rst2man=	Fixing rst2man name used by pkgsrc due to versioning.
SUBST_STAGE.rst2man=	pre-configure
SUBST_FILES.rst2man=	docs/meson.build
SUBST_SED.rst2man=	-e "s,'rst2man','rst2man-${PYVERSSUFFIX}',g"

post-extract:
	${CHMOD} a+x ${WRKSRC}/build-aux/gen-thumbnailer.py

.include "../../mk/bsd.prefs.mk"

SUBST_CLASSES+=		dyld
SUBST_STAGE.dyld=	pre-configure
SUBST_FILES.dyld=	gdk-pixbuf/meson.build \
			tests/meson.build \
			thumbnailer/meson.build
.if ${OPSYS} == "Darwin"
SUBST_SED.dyld=		-e 's|@LD_LIBRARY_PATH@|DYLD_LIBRARY_PATH|g'
.else
SUBST_SED.dyld=		-e 's|@LD_LIBRARY_PATH@|LD_LIBRARY_PATH|g'
.endif

MESON_ARGS+=			-D installed_tests=false
# https://gitlab.gnome.org/GNOME/gdk-pixbuf/-/merge_requests/169
MESON_ARGS+=			-D others=enabled
MESON_ARGS+=			-D glycin=disabled
PKGCONFIG_OVERRIDE_STAGE=	pre-install
PKGCONFIG_OVERRIDE=		output/meson-private/gdk-pixbuf-2.0.pc

PLIST_VARS+=		native
PLIST.native=	yes

# Resolve options before cross tooling so PKG_DEFAULT_OPTIONS+=-introspection
# can skip the SSH target-query path (loaders.cache / GIR) on hosts without a guest.
.include "options.mk"

.if ${USE_CROSS_COMPILE:tl} == "yes"

# Native GLib codegen is always required for the shared library itself.
TOOL_DEPENDS+=			glib2-tools>=0:../../devel/glib2-tools
MESON_BINARIES+=		glib-genmarshal glib-mkenums
MESON_BINARY.glib-genmarshal=	${TOOLBASE}/bin/glib-genmarshal
MESON_BINARY.glib-mkenums=	${TOOLBASE}/bin/glib-mkenums

.  if !empty(PKG_OPTIONS:Mintrospection)
# Introspection and loaders.cache/MIME generation need a live target query.
.    if empty(EMBERBSD_SDK_SOURCE:M/*) || !exists(${EMBERBSD_SDK_SOURCE}/src/emberbsd_sdk/__init__.py)
PKG_FAIL_REASON+= "GdkPixbuf cross tools require an explicit SDK host API source"
.    endif
EMBERBSD_GI_MESON_OPTIONS=	no
.include "../../devel/gobject-introspection/cross.mk"
MESON_CROSS_VARS+=	emberbsd_gi_cross emberbsd_gi_ldd_wrapper emberbsd_pixbuf_runner emberbsd_pixbuf_python
MESON_CROSS.emberbsd_gi_cross=	true
MESON_CROSS.emberbsd_pixbuf_python=	'${TOOL_PYTHONBIN}'
MESON_CROSS.emberbsd_gi_ldd_wrapper=	'${EMBERBSD_GI_FILESDIR}/elf-needed.sh'
MESON_CROSS.emberbsd_pixbuf_runner=	['${EMBERBSD_CROSS_BUILD_PYTHON}', '-E', '-S', '${FILESDIR}/target-tools.py']
MAKE_ENV+=	EMBERBSD_SDK_SOURCE=${EMBERBSD_SDK_SOURCE:Q}
pre-configure: emberbsd-pixbuf-native
.PHONY: emberbsd-pixbuf-native
emberbsd-pixbuf-native:
	${RUN}${SETENV} EMBERBSD_SDK_SOURCE=${EMBERBSD_SDK_SOURCE:Q} EMBERBSD_GI_QUERY_CONFIG=${EMBERBSD_GI_QUERY_CONFIG:Q} EMBERBSD_GI_TARGET=${_EMBER_GI_TARGET:Q} ${EMBERBSD_CROSS_BUILD_PYTHON} -E -S ${FILESDIR}/target-tools.py --check ${WRKDIR} ${CROSS_DESTDIR} ${TOOLDIR}/bin/${_EMBER_GI_TRIPLET}-readelf
.  endif

.else

PLIST.native=	yes
MAKE_ENV+=	LD_LIBRARY_PATH=${WRKSRC}/output/gdk-pixbuf
# For Darwin
MAKE_ENV+=	DYLD_LIBRARY_PATH=${WRKSRC}/output/gdk-pixbuf

.endif

PYTHON_FOR_BUILD_ONLY=	tool
REPLACE_PYTHON+=	build-aux/gen-thumbnailer.py

.include "../../lang/python/application.mk"
.include "../../lang/python/tool.mk"

_BUILDING_GTK2= yes
.include "loaders.mk"

.include "../../devel/meson/build.mk"
.include "../../databases/shared-mime-info/buildlink3.mk"
# not needed unless 'documentation' option is turned on
#.include "../../devel/py-gi-docgen/buildlink3.mk"
BUILDLINK_API_DEPENDS.glib2+= glib2>=2.37.2
.include "../../devel/glib2/buildlink3.mk"
.include "../../graphics/png/buildlink3.mk"
.include "../../graphics/tiff/buildlink3.mk"
.include "../../mk/jpeg.buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

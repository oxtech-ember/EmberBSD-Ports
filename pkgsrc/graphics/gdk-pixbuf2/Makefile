# $NetBSD: Makefile,v 1.82 2026/09/02 19:02:36 wiz Exp $

DISTNAME=	gdk-pixbuf-2.44.8
PKGNAME=	${DISTNAME:S/pixbuf/pixbuf2/}
PKGREVISION=	5
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

# Resolve options before cross tooling so PKG_DEFAULT_OPTIONS+=-introspection
# skips the introspection and loaders.cache/MIME cross path.
.include "options.mk"

.if ${USE_CROSS_COMPILE:tl} == "yes"

# Native GLib codegen is always required for the shared library itself.
TOOL_DEPENDS+=			glib2-tools>=0:../../devel/glib2-tools
MESON_BINARIES+=		glib-genmarshal glib-mkenums
MESON_BINARY.glib-genmarshal=	${TOOLBASE}/bin/glib-genmarshal
MESON_BINARY.glib-mkenums=	${TOOLBASE}/bin/glib-mkenums

.  if !empty(PKG_OPTIONS:Mintrospection)
# The GIR replays stored GI dumps, and loaders.cache/MIME generation replays
# stored target data from files/target-data/PLATFORM (files/pixbuf_data.py),
# so the default build runs nothing on a target. EMBERBSD_GI_DUMP_MODE=live
# or capture queries a target instead (profiles/common-graphics/cross/gi-dumps.md).
EMBERBSD_GI_MESON_OPTIONS=	no
# thumbnailer is built in cross only on the emberbsd_gi_cross path.
PLIST.native=	yes
.include "../../devel/gobject-introspection/cross.mk"
MESON_CROSS_VARS+=	emberbsd_gi_cross emberbsd_gi_ldd_wrapper emberbsd_pixbuf_runner emberbsd_pixbuf_python
MESON_CROSS.emberbsd_gi_cross=	true
MESON_CROSS.emberbsd_pixbuf_python=	'${TOOL_PYTHONBIN}'
MESON_CROSS.emberbsd_gi_ldd_wrapper=	'${EMBERBSD_GI_FILESDIR}/elf-needed.sh'
MESON_CROSS.emberbsd_pixbuf_runner=	['${EMBERBSD_CROSS_BUILD_PYTHON}', '-E', '-S', '${FILESDIR}/target-tools.py']
EMBERBSD_PIXBUF_DATA_DIR=	${PKGDIR}/files/target-data/${_EMBER_GI_PLATFORM}
MAKE_ENV+=	EMBERBSD_PIXBUF_DATA_DIR=${EMBERBSD_PIXBUF_DATA_DIR:Q}
MAKE_ENV+=	EMBERBSD_SDK_SOURCE=${EMBERBSD_SDK_SOURCE:Q}
pre-configure: emberbsd-pixbuf-native
.PHONY: emberbsd-pixbuf-native
# The shared GI include checks the SDK and query inputs at configure time.
emberbsd-pixbuf-native: emberbsd-gi-inputs
.    if "${EMBERBSD_GI_DUMP_MODE}" == "replay"
	${RUN}${TEST} -f ${EMBERBSD_PIXBUF_DATA_DIR:Q}/loaders.cache && ${TEST} -f ${EMBERBSD_PIXBUF_DATA_DIR:Q}/mime-types.txt || { ${ERROR_MSG} "No stored GdkPixbuf target data for ${_EMBER_GI_PLATFORM} in ${PKGPATH}; capture them from an EmberBSD target (profiles/common-graphics/cross/gi-dumps.md)"; exit 1; }
.    else
	${RUN}${SETENV} EMBERBSD_SDK_SOURCE=${EMBERBSD_SDK_SOURCE:Q} EMBERBSD_GI_QUERY_CONFIG=${EMBERBSD_GI_QUERY_CONFIG:Q} EMBERBSD_GI_TARGET=${_EMBER_GI_TARGET:Q} ${EMBERBSD_CROSS_BUILD_PYTHON} -E -S ${FILESDIR}/target-tools.py --check ${WRKDIR} ${CROSS_DESTDIR} ${TOOLDIR}/bin/${_EMBER_GI_TRIPLET}-readelf
.    endif
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

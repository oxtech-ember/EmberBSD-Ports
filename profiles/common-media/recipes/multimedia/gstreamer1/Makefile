# $NetBSD: Makefile,v 1.74 2026/09/02 19:03:44 wiz Exp $

.include "version.mk"

DISTNAME=	gstreamer-${GST_VERSION}
PKGNAME=	${DISTNAME:S/gstreamer/gstreamer1/}
PKGREVISION=	1
CATEGORIES=	multimedia
MASTER_SITES=	https://gstreamer.freedesktop.org/src/gstreamer/
EXTRACT_SUFX=	.tar.xz

TOOL_DEPENDS+=	glib2-introspection-[0-9]*:../../devel/glib2-introspection
# Installed Gst typelibs import GLib/GObject, now split from the base library.
DEPENDS+=	glib2-introspection>=2.90.1nb1:../../devel/glib2-introspection

COMMENT=	Open source multimedia framework

USE_TOOLS+=	bison flex perl pkg-config xgettext
TEST_TARGET=	check
FLEX_REQD+=	2.5.31

LDFLAGS.SunOS+=		-lsocket -lnsl -lrt

PKGCONFIG_OVERRIDE+=		output/meson-private/*.pc
PKGCONFIG_OVERRIDE_STAGE=	pre-install

CHECK_PORTABILITY_SKIP+=	hooks/pre-commit.hook

REPLACE_TOOL_PYTHON+=	gst/parse/get_flex_version.py
# This helper is installed for execution on the target.
REPLACE_PYTHON+=	docs/gst-plugins-doc-cache-generator.py
REPLACE_TOOL_PYTHON+=	gst/parse/gen_grammar.py.in
REPLACE_TOOL_PYTHON+=	gst/parse/gen_lex.py.in
REPLACE_TOOL_PYTHON+=	scripts/dist-translations.py
REPLACE_TOOL_PYTHON+=	scripts/extract-release-date-from-doap-file.py

MESON_ARGS+=		-Dptp-helper=disabled

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# Host generators, target GType queries; preserve all GIR and typelib outputs.
TOOL_DEPENDS+= glib2-tools>=2.90.1:../../devel/glib2-tools
EMBERBSD_GI_MESON_OPTIONS= no
.include "../../devel/gobject-introspection/cross.mk"
MESON_ARGS+= -Dintrospection=enabled
MESON_BINARIES+= glib-mkenums glib-genmarshal g-ir-scanner g-ir-compiler
MESON_BINARY.glib-mkenums= ${TOOLBASE}/bin/glib-mkenums
MESON_BINARY.glib-genmarshal= ${TOOLBASE}/bin/glib-genmarshal
MESON_BINARY.g-ir-scanner= ${TOOLBASE}/bin/g-ir-scanner
MESON_BINARY.g-ir-compiler= ${TOOLBASE}/bin/g-ir-compiler
MESON_CROSS_VARS+= emberbsd_gi_cross emberbsd_gi_ldd_wrapper
MESON_CROSS.emberbsd_gi_cross= true
MESON_CROSS.emberbsd_gi_ldd_wrapper= '${EMBERBSD_GI_FILESDIR}/elf-needed.sh'
.endif

# for tests
MAKE_ENV+=		LD_LIBRARY_PATH=${WRKSRC}/output/gst:${WRKSRC}/output/libs/gst/check:${WRKSRC}/output/libs/gst/base:${WRKSRC}/output/libs/gst/controller:${WRKSRC}/output/libs/gst/net:${WRKSRC}/output/plugins/elements:${WRKSRC}/output/plugins/tracers

# test status as of 1.18.5
#Ok:                 66
#Expected Fail:      0
#Fail:               39
#Unexpected Pass:    0
#Skipped:            1
#Timeout:            0

.include "../../lang/python/application.mk"
.include "../../devel/meson/build.mk"
# test framework, only needed at test time
BUILDLINK_DEPMETHOD.check=	build
.include "../../devel/check/buildlink3.mk"
.include "../../devel/glib2/buildlink3.mk"
BUILDLINK_DEPMETHOD.gobject-introspection=	build
.include "../../devel/gobject-introspection/buildlink3.mk"
.include "../../devel/gmp/buildlink3.mk"
.include "../../math/gsl/buildlink3.mk"
.include "../../mk/atomic64.mk"
.include "../../mk/bsd.pkg.mk"

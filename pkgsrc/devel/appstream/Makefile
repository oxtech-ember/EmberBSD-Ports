# $NetBSD: Makefile,v 1.35 2026/09/02 19:01:21 wiz Exp $

DISTNAME=	appstream-1.1.6
PKGREVISION=	2
CATEGORIES=	devel
MASTER_SITES=	${MASTER_SITE_GITHUB:=ximion/}
GITHUB_TAG=	v${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/ximion/appstream
COMMENT=	Tools and libraries to work with AppStream metadata
LICENSE=	gnu-lgpl-v2.1

TOOL_DEPENDS+=	docbook-xsl-[0-9]*:../../textproc/docbook-xsl
TOOL_DEPENDS+=	glib2-introspection-[0-9]*:../../devel/glib2-introspection
TOOL_DEPENDS+=	gperf-[0-9]*:../../devel/gperf
TOOL_DEPENDS+=	libxslt-[0-9]*:../../textproc/libxslt

USE_CC_FEATURES=	c17
USE_LANGUAGES=		c c++
USE_PKGLOCALEDIR=	yes
USE_TOOLS+=		itstool msgfmt pkg-config

MESON_ARGS+=	-Dapidocs=false
MESON_ARGS+=	-Dbash-completion=false
MESON_ARGS+=	-Dsystemd=false
# for running a tool during the build
MAKE_ENV+=	LD_LIBRARY_PATH=${WRKSRC}/output/src
# for Darwin
MAKE_ENV+=	DYLD_LIBRARY_PATH=${WRKSRC}/output/src

PKGCONFIG_OVERRIDE+=		output/meson-private/appstream.pc
PKGCONFIG_OVERRIDE_STAGE=	post-configure

.include "../../mk/bsd.prefs.mk"

# The sysroot g-ir-scanner cannot run on the build host.
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
MESON_ARGS+=	-Dgir=false
# The man-page stylesheet path is the target prefix. The host cannot read it.
MESON_ARGS+=	-Dman=false
.else
PLIST.gir=	yes
PLIST.man=	yes
.endif

# Hard-coded path to /usr/include for libstemmer.h.
SUBST_CLASSES+=		paths
SUBST_STAGE.paths=	pre-configure
SUBST_MESSAGE.paths=	Fixing absolute paths.
SUBST_FILES.paths=	meson.build
SUBST_SED.paths=	-e 's,/usr/include,${PREFIX}/include,g'
# libstemmer's include path is hard-coded. On a cross build that path is
# inside the sysroot, not on the build host.
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
SUBST_SED.paths+=	-e 's,/usr/pkg/include,${EMBERBSD_CROSS_SYSROOT}/usr/pkg/include,g'
.else
SUBST_SED.paths+=	-e 's,/usr/pkg/include,${PREFIX}/include,g'
.endif

.include "../../devel/wayland/platform.mk"
.if !empty(PLATFORM_SUPPORTS_WAYLAND:Myes)
.include "../../devel/wayland/buildlink3.mk"
.endif

.include "../../archivers/zstd/buildlink3.mk"
.include "../../devel/glib2/buildlink3.mk"
.include "../../devel/gobject-introspection/buildlink3.mk"
.include "../../devel/meson/build.mk"
.include "../../textproc/libfyaml/buildlink3.mk"
.include "../../textproc/libstemmer/buildlink3.mk"
.include "../../textproc/libxmlb/buildlink3.mk"
.include "../../www/curl/buildlink3.mk"
.include "options.mk"
.include "../../mk/bsd.pkg.mk"

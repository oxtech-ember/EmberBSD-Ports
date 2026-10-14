# $NetBSD$

DISTNAME=	glycin-2.0.8
CATEGORIES=	graphics gnome
MASTER_SITES=	${MASTER_SITE_GNOME:=sources/glycin/2.0/}
EXTRACT_SUFX=	.tar.xz

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://gitlab.gnome.org/GNOME/glycin
COMMENT=	Sandboxed and extendable image decoding (libglycin C bindings)
LICENSE=	gnu-lgpl-v2.1 AND mpl-2.0

USE_LANGUAGES+=	c
USE_TOOLS+=	pkg-config

# libglycin only: the loader processes and the thumbnailer stay separate.
MESON_ARGS+=	-Dlibglycin=true
MESON_ARGS+=	-Dlibglycin-gtk4=false
MESON_ARGS+=	-Dglycin-loaders=false
MESON_ARGS+=	-Dglycin-thumbnailer=false
MESON_ARGS+=	-Dintrospection=false
MESON_ARGS+=	-Dvapi=false
MESON_ARGS+=	-Dtests=false

# Cross: the version script must run on the host; macOS python3 is too old
# for tomllib, so point the shebang at the build python.
SUBST_CLASSES+=		pyfix
SUBST_STAGE.pyfix=		pre-configure
SUBST_FILES.pyfix=		build-aux/crates-version.py
SUBST_SED.pyfix=		-e "s,/usr/bin/python3,/private/tmp/ember-common-stack/host/bin/python3.14,"

.include "../../mk/bsd.prefs.mk"

# This chain tree is cross-only; unconditioned so dependency walkers
# in child bmake processes parse the same RUST_TYPE.
.include "cross.mk"

.include "cargo-depends.mk"
.include "../../devel/meson/build.mk"
BUILDLINK_API_DEPENDS.glib2+=	glib2>=2.66
.include "../../devel/glib2/buildlink3.mk"
.include "../../devel/glib2/schemas.mk"
.include "../../graphics/lcms2/buildlink3.mk"
.include "../../fonts/fontconfig/buildlink3.mk"
.include "../../lang/rust/cargo.mk"
.include "../../mk/bsd.pkg.mk"

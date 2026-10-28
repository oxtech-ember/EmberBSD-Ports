# $NetBSD$

DISTNAME=	glycin-2.2.3
PKGREVISION=	3
CATEGORIES=	graphics gnome
MASTER_SITES=	${MASTER_SITE_GNOME:=sources/glycin/2.2/}
EXTRACT_SUFX=	.tar.xz

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://gitlab.gnome.org/GNOME/glycin
COMMENT=	Sandboxed and extendable image decoding (libglycin C bindings)
LICENSE=	gnu-lgpl-v2.1 AND mpl-2.0

USE_LANGUAGES+=	c
USE_TOOLS+=	pkg-config
PYTHON_VERSIONS_ACCEPTED= 315
PYTHON_FOR_BUILD_ONLY= tool

# libglycin only: the loader processes and the thumbnailer stay separate.
MESON_ARGS+=	-Dlibglycin=true
MESON_ARGS+=	-Dlibglycin-gtk4=false
MESON_ARGS+=	-Dglycin-loaders=false
MESON_ARGS+=	-Dglycin-thumbnailer=false
MESON_ARGS+=	-Dintrospection=false
MESON_ARGS+=	-Dvapi=false
MESON_ARGS+=	-Dtests=false

.include "../../mk/bsd.prefs.mk"

# This chain tree is cross-only; unconditioned so dependency walkers
# in child bmake processes parse the same RUST_TYPE.
.include "cross.mk"

.include "cargo-depends.mk"
.include "../../devel/meson/build.mk"
# Outside Linux, glycin decodes in-process with Rust decoders; it needs no
# libseccomp, fontconfig or lcms2.
BUILDLINK_API_DEPENDS.glib2+=	glib2>=2.60
.include "../../devel/glib2/buildlink3.mk"
.include "../../lang/python/tool.mk"
.include "../../lang/rust/cargo.mk"
EMBER_CARGO_PREFIX?= ${TOOLBASE}
EMBER_CARGO_PATCH_SET= yes
.include "../../lang/rust/emberbsd-cargo-patches.mk"
.include "../../mk/bsd.pkg.mk"

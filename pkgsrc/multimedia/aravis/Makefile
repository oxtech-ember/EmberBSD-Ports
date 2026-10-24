# $NetBSD$

DISTNAME=	aravis-0.8.36
CATEGORIES=	multimedia
MASTER_SITES=	${MASTER_SITE_GITHUB:=AravisProject/}
GITHUB_RELEASE=	${PKGVERSION_NOREV}
EXTRACT_SUFX=	.tar.xz

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/AravisProject/aravis
COMMENT=	Library for GenICam GigE Vision and USB3 Vision cameras
LICENSE=	gnu-lgpl-v2.1

USE_TOOLS+=	pkg-config
USE_LANGUAGES=	c c++

# Library and command line tools only; the GTK viewer, the GStreamer
# plugin and introspection are separate consumers. Packet sockets are
# Linux-only.
MESON_ARGS+=	-Dviewer=disabled
MESON_ARGS+=	-Dgst-plugin=disabled
MESON_ARGS+=	-Dusb=enabled
MESON_ARGS+=	-Dpacket-socket=disabled
MESON_ARGS+=	-Dintrospection=disabled
MESON_ARGS+=	-Ddocumentation=disabled
MESON_ARGS+=	-Dtests=true

PKGCONFIG_OVERRIDE_STAGE=	pre-install
PKGCONFIG_OVERRIDE+=		output/meson-private/aravis-0.8.pc

.include "../../devel/meson/build.mk"
.include "../../devel/glib2/buildlink3.mk"
.include "../../devel/libusb1/buildlink3.mk"
.include "../../devel/zlib/buildlink3.mk"
.include "../../textproc/libxml2/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

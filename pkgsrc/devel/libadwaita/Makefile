# $NetBSD: Makefile,v 1.40 2026/09/02 19:01:35 wiz Exp $

DISTNAME=	libadwaita-1.10.0
CATEGORIES=	devel
MASTER_SITES=	${MASTER_SITE_GNOME:=sources/${PKGBASE}/${PKGVERSION_NOREV:R}/}
EXTRACT_SUFX=	.tar.xz

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://gitlab.gnome.org/GNOME/libadwaita/
COMMENT=	Building blocks for modern GNOME applications
LICENSE=	gnu-lgpl-v2.1

USE_TOOLS+=	msgfmt pkg-config

PKGCONFIG_OVERRIDE+=	output/meson-private/libadwaita-1.pc

PKGCONFIG_OVERRIDE_STAGE=	post-configure

MESON_ARGS+=	--wrap-mode=nofallback

TEST_ENV+=	LD_LIBRARY_PATH=${WRKSRC}/output/src

.include "options.mk"
.include "../../converters/fribidi/buildlink3.mk"
.include "../../devel/ministream/buildlink3.mk"
.include "../../devel/gettext-tools/msgfmt-desktop.mk"
BUILDLINK_API_DEPENDS.glib2+=	glib2>=2.89.3
.include "../../devel/glib2/buildlink3.mk"
.include "../../devel/meson/build.mk"
BUILDLINK_API_DEPENDS.gtk4+=	gtk4>=4.23.1
.include "../../x11/gtk4/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

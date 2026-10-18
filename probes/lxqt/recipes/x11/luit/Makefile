# $NetBSD: Makefile,v 1.16 2022/11/09 13:14:23 joerg Exp $

DISTNAME=		luit-20260907
PKGNAME=		luit-2.0.20260907
PKGREVISION=		3
CATEGORIES=		x11
MASTER_SITES=		https://invisible-island.net/archives/luit/
EXTRACT_SUFX=		.tgz

MAINTAINER=		pkgsrc-users@NetBSD.org
HOMEPAGE=		https://invisible-island.net/luit/
COMMENT=		Locale and ISO 2022 support for Unicode terminals
LICENSE=		mit

GNU_CONFIGURE=		yes
USE_TOOLS+=		pkg-config

CONFIGURE_ENV+=		APP_MAN_SUFFIX=1
DEPENDS+=		encodings>=1.1.0:../../fonts/encodings
CONFIGURE_ARGS+=	--with-encodings-dir=${PREFIX}/share/fonts/X11/encodings/encodings.dir
CONFIGURE_ARGS+=	--with-locale-alias=${BUILDLINK_PREFIX.libX11}/share/X11/locale/locale.alias

.include "../../converters/libiconv/buildlink3.mk"
.include "../../devel/zlib/buildlink3.mk"
.include "../../x11/libX11/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

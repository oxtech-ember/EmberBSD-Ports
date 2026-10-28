# $NetBSD$
#
# EmberBSD port: libsigrok 0.5.2 (sigrok), first pkgsrc recipe for the
# diagnostics kit (R10 stage three). Board kit keeps only the demo
# driver: no USB/serial test hardware is attached to the stand yet.

DISTNAME=	libsigrok-0.5.2
CATEGORIES=	devel
MASTER_SITES=	https://sigrok.org/download/source/libsigrok/
# Fedora keeps the same upstream archive under its SHA512 in distinfo.
MASTER_SITES+=	https://src.fedoraproject.org/repo/pkgs/libsigrok/${DISTNAME}${EXTRACT_SUFX}/sha512/cf673dad6280302d69050c29490621f66c6d6a73932d019a53ec3501316d3f2e23e7667a04f866dbe6ed73f86a63de73d2173e2b6cea563631d705e06f887092/
EXTRACT_SUFX=	.tar.gz

MAINTAINER=	ports@emberbsd.invalid
HOMEPAGE=	https://sigrok.org/wiki/Libsigrok
COMMENT=	Signal acquisition library for logic analyzers (demo driver)
LICENSE=	gnu-gpl-v3

GNU_CONFIGURE=	yes
USE_LIBTOOL=	yes
USE_TOOLS+=	pkg-config gmake perl
USE_LANGUAGES=	c c++

CONFIGURE_ARGS+=	--disable-all-drivers --enable-demo
CONFIGURE_ARGS+=	--disable-cxx --disable-python --disable-ruby
CONFIGURE_ARGS+=	--disable-parport --disable-java

.include "../../archivers/libzip/buildlink3.mk"
.include "../../devel/glib2/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

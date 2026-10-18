# $NetBSD$
# Origin: EmberBSD (AI-assisted); complete upstream Unix/X11 provider.

DISTNAME=	libspnav-1.2
CATEGORIES=	x11 devel
MASTER_SITES=	${MASTER_SITE_GITHUB:=FreeSpacenav/}
GITHUB_RELEASE=	v${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/FreeSpacenav/libspnav/
COMMENT=	Space-navigation client library with Unix and X11 interfaces
LICENSE=	modified-bsd

GCC_REQD+=	16.2
USE_LANGUAGES=	c
USE_TOOLS+=	gmake
HAS_CONFIGURE=	yes
CONFIGURE_ARGS+=	--prefix=${PREFIX} --enable-x11
CONFIGURE_ENV+=	CFLAGS=${CFLAGS:Q} LDFLAGS=${LDFLAGS:Q}

# The custom upstream build must use the target OS, compiler and pkgsrc paths.
SPNAV_CPPFLAGS=	-I. ${CPPFLAGS}
MAKE_FLAGS+=	CC=${CC:Q} AR=${AR:Q} target_os=${OPSYS:Q}
MAKE_FLAGS+=	incpaths=${SPNAV_CPPFLAGS:Q} libpaths=
MAKE_FLAGS+=	INSTALL_DATA=${INSTALL_DATA:Q} INSTALL_LIB=${INSTALL_LIB:Q}

INSTALLATION_DIRS+=	share/licenses/libspnav

post-install:
	${INSTALL_DATA} ${WRKSRC}/LICENSE \
	    ${DESTDIR}${PREFIX}/share/licenses/libspnav/LICENSE

.include "../../x11/libX11/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

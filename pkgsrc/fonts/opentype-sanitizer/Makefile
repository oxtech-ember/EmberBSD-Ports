# $NetBSD$
# Origin: EmberBSD contributors (AI-assisted).
DISTNAME=	ots-9.3.0
PKGNAME=	${DISTNAME:S/^ots-/opentype-sanitizer-/}
CATEGORIES=	fonts
MASTER_SITES=	${MASTER_SITE_GITHUB:=khaledhosny/}
GITHUB_PROJECT=	ots
GITHUB_TAG=	v${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/khaledhosny/ots
COMMENT=	OpenType and WOFF font sanitizer
LICENSE=	modified-bsd

USE_LANGUAGES=	c c++
USE_TOOLS+=	pkg-config
MESON_ARGS+=	--wrap-mode=nofallback -Dtests=false
INSTALLATION_DIRS+= share/licenses/opentype-sanitizer

post-install:
	${INSTALL_DATA} ${WRKSRC}/LICENSE ${DESTDIR}${PREFIX}/share/licenses/opentype-sanitizer/LICENSE

.include "../../devel/meson/build.mk"
.include "../../archivers/lz4/buildlink3.mk"
.include "../../devel/zlib/buildlink3.mk"
.include "../../fonts/woff2/buildlink3.mk"
.include "../../graphics/freetype2/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

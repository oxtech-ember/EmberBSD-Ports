# Kit delta over the stock pkgsrc recipe: library-only build without
# the nihtest/python regression machinery (see profile README).
# $NetBSD: Makefile,v 1.85 2026/05/14 16:40:22 ryoon Exp $

DISTNAME=		libzip-1.11.4
PKGREVISION=		3
CATEGORIES=		archivers devel
MASTER_SITES=		https://libzip.org/download/
MASTER_SITES+=		${MASTER_SITE_GITHUB:=nih-at/}
GITHUB_RELEASE=		v${PKGVERSION_NOREV}
EXTRACT_SUFX=		.tar.xz

MAINTAINER=		wiz@NetBSD.org
HOMEPAGE=		https://libzip.org/
COMMENT=		C library to manipulate zip archives
LICENSE=		modified-bsd

# EmberBSD kit delta: board-side libzip is the library only; the
# regression machinery drags a nihtest/python dependency onto targets.
CMAKE_CONFIGURE_ARGS+=	-DBUILD_REGRESS=OFF -DBUILD_EXAMPLES=OFF
MAKE_ENV+=		LD_LIBRARY_PATH=${WRKSRC}/${CMAKE_BUILD_DIR}/lib
# for Darwin
MAKE_ENV+=		DYLD_LIBRARY_PATH=${WRKSRC}/${CMAKE_BUILD_DIR}/lib

.include "options.mk"

.include "../../devel/cmake/build.mk"
.include "../../devel/zlib/buildlink3.mk"
.include "../../archivers/bzip2/buildlink3.mk"
.include "../../archivers/xz/buildlink3.mk"
.include "../../archivers/zstd/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

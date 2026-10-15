# Origin: EmberBSD (AI-assisted). First port; Union from Plasma 6.8 needs it.

DISTNAME=	rapidyaml-0.16.0
PKGNAME=	ryml-0.16.0
CATEGORIES=	devel
MASTER_SITES=	${MASTER_SITE_GITHUB:=biojppm/}
GITHUB_PROJECT=	rapidyaml
GITHUB_TAG=	v0.16.0
EXTRACT_SUFX=	.tar.gz

HOMEPAGE=	https://github.com/biojppm/rapidyaml
COMMENT=	Library to parse and emit YAML, meant for speed and inline use
LICENSE=	mit

.include "../../mk/bsd.prefs.mk"

USE_CMAKE=	yes
USE_LANGUAGES=	c c++
USE_TOOLS+=	pkg-config
CMAKE_CONFIGURE_ARGS+= -DRYML_BUILD_TESTS=OFF
CMAKE_CONFIGURE_ARGS+= -DRYML_BUILD_TOOLS=OFF
CMAKE_CONFIGURE_ARGS+= -DRYML_BUILD_BENCHMARKS=OFF
CMAKE_CONFIGURE_ARGS+= -DBUILD_SHARED_LIBS=ON

.include "../../mk/bsd.pkg.mk"

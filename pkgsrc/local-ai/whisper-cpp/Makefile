# EmberBSD: CPU runtime package, based on upstream whisper.cpp 1.9.5.
DISTNAME=	whisper.cpp-1.9.5
PKGNAME=	whisper-cpp-1.9.5
CATEGORIES=	audio
MASTER_SITES=	${MASTER_SITE_GITHUB:=ggml-org/}
GITHUB_PROJECT=	whisper.cpp
GITHUB_TAG=	d1be6fde11ac6e0407606b4e42fe72d34add8037
WRKSRC=		${WRKDIR}/${GITHUB_PROJECT}-${GITHUB_TAG}

HOMEPAGE=	https://github.com/ggml-org/whisper.cpp
COMMENT=	Local CPU speech recognition with Whisper models
LICENSE=	mit AND unlicense

AI_PROGRAMS=	whisper-cli whisper-bench whisper-quantize
BUILD_TARGET=	${AI_PROGRAMS}

CMAKE_CONFIGURE_ARGS+=	-C ${.CURDIR}/package.cmake

.include "../cpu.mk"
.include "../../mk/bsd.pkg.mk"

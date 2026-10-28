# EmberBSD: CPU runtime package, based on upstream llama.cpp 0.6.0.
DISTNAME=	llama.cpp-0.6.0
PKGNAME=	llama-cpp-0.6.0
PKGREVISION=	1
CATEGORIES=	misc
MASTER_SITES=	${MASTER_SITE_GITHUB:=ggml-org/}
GITHUB_PROJECT=	llama.cpp
GITHUB_TAG=	8345f333951c661d166b00e6f9362e553768f292
WRKSRC=		${WRKDIR}/${GITHUB_PROJECT}-${GITHUB_TAG}

HOMEPAGE=	https://github.com/ggml-org/llama.cpp
COMMENT=	Local CPU language model inference and HTTP server
LICENSE=	mit AND 2-clause-bsd AND unlicense

AI_PROGRAMS=	llama-cli llama-completion llama-server llama-bench llama-quantize
AI_NOTICES=	vendor/cpp-httplib/LICENSE
BUILD_TARGET=	${AI_PROGRAMS}

CMAKE_CONFIGURE_ARGS+=	-C ${.CURDIR}/package.cmake
CMAKE_CONFIGURE_ARGS+=	-DLLAMA_BUILD_COMMIT=${GITHUB_TAG}

.include "../cpu.mk"
.include "../../mk/bsd.pkg.mk"

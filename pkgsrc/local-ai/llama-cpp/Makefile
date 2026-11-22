# EmberBSD: CPU runtime package, based on upstream llama.cpp 1.0.0.
DISTNAME=	llama.cpp-1.0.0
PKGNAME=	llama-cpp-1.0.0
CATEGORIES=	misc
MASTER_SITES=	${MASTER_SITE_GITHUB:=ggml-org/}
GITHUB_PROJECT=	llama.cpp
GITHUB_TAG=	b1b770d90d94cad9e9ea5b993bdbc383a522fb28
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

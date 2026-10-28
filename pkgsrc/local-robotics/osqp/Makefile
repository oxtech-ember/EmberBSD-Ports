# SPDX-License-Identifier: MIT
# Origin: EmberBSD, AI-assisted native OSQP library package.
DISTNAME=	osqp-1.0.0
CATEGORIES=	math
MASTER_SITES=	${MASTER_SITE_GITHUB:=osqp/}
GITHUB_PROJECT=	osqp
GITHUB_TAG=	v${PKGVERSION_NOREV}

QDLDL_VERSION=	0.1.9
DISTFILES=	${DEFAULT_DISTFILES} qdldl-${QDLDL_VERSION}.tar.gz
SITES.qdldl-${QDLDL_VERSION}.tar.gz= \
	-https://codeload.github.com/osqp/qdldl/tar.gz/refs/tags/v${QDLDL_VERSION}

HOMEPAGE=	https://osqp.org/
COMMENT=	Operator splitting solver for convex quadratic programs
LICENSE=	apache-2.0 AND modified-bsd

USE_LANGUAGES=		c c++
USE_CC_FEATURES=		c99
CMAKE_REQD+=		3.18
CMAKE_CONFIGURE_ARGS+=	-C ${.CURDIR}/features.cmake
CMAKE_CONFIGURE_ARGS+=	-DOSQP_VERSION=${PKGVERSION_NOREV}
CMAKE_CONFIGURE_ARGS+=	-DFETCHCONTENT_SOURCE_DIR_QDLDL=${WRKDIR}/qdldl-${QDLDL_VERSION}

INSTALLATION_DIRS+=	share/licenses/osqp

post-install:
	${INSTALL_DATA} ${WRKSRC}/LICENSE \
	    ${DESTDIR}${PREFIX}/share/licenses/osqp/OSQP-Apache-2.0
	${INSTALL_DATA} ${WRKSRC}/NOTICE \
	    ${DESTDIR}${PREFIX}/share/licenses/osqp/OSQP-NOTICE
	${INSTALL_DATA} ${WRKDIR}/qdldl-${QDLDL_VERSION}/LICENSE \
	    ${DESTDIR}${PREFIX}/share/licenses/osqp/QDLDL-Apache-2.0
	${INSTALL_DATA} ${WRKSRC}/algebra/_common/lin_sys/qdldl/amd/LICENSE \
	    ${DESTDIR}${PREFIX}/share/licenses/osqp/AMD-BSD-3-Clause
	${INSTALL_DATA} ${FILESDIR}/SOURCE \
	    ${DESTDIR}${PREFIX}/share/licenses/osqp/SOURCE

.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"

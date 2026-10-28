# $NetBSD: Makefile,v 1.1 2025/09/28 16:25:06 bsiegert Exp $

DISTNAME=	rpcsvc-proto-1.4.4
CATEGORIES=	devel
MASTER_SITES=	${MASTER_SITE_GITHUB:=thkukuk/rpcsvc-proto/releases/download/v${PKGVERSION_NOREV}/}
EXTRACT_SUFX=	.tar.xz

MAINTAINER=	bsiegert@NetBSD.org
HOMEPAGE=	https://github.com/thkukuk/rpcsvc-proto/
COMMENT=	RPCSVC protocol definitions from glibc
LICENSE=	modified-bsd

# Darwin hosts use rpcgen as the native tool for NetBSD cross builds.
ONLY_FOR_PLATFORM=	Linux-*-* Darwin-*-*

GNU_CONFIGURE=	yes

# rpcgen runs "cpp" from PATH, which can be a compiler driver without -E.
# The build-time headers then are empty. Select a real preprocessor.
RPCGEN_CPPDIR=	${WRKDIR}/rpcgen-cpp
MAKE_FLAGS+=	RPCGENFLAGS="-Y ${RPCGEN_CPPDIR}"

pre-build:
	${MKDIR} ${RPCGEN_CPPDIR}
	${PRINTF} '#!%s\nexec %s -E "$$@"\n' ${SH:Q} ${CC:Q} > ${RPCGEN_CPPDIR}/cpp
	${CHMOD} +x ${RPCGEN_CPPDIR}/cpp

.include "../../mk/bsd.pkg.mk"

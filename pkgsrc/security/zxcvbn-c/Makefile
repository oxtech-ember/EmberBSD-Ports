# $NetBSD: Makefile,v 1.3 2025/09/22 22:33:44 ryoon Exp $

DISTNAME=	zxcvbn-c-2.7
PKGREVISION= 2
CATEGORIES=	security
MASTER_SITES=	${MASTER_SITE_GITHUB:=tsyrogit/}
GITHUB_PROJECT=	zxcvbn-c
GITHUB_TAG=	v${PKGVERSION_NOREV}

MAINTAINER=	ryoon@NetBSD.org
HOMEPAGE=	https://github.com/tsyrogit/zxcvbn-c/
COMMENT=	Password strength estimator
LICENSE=	mit

MAKE_JOBS_SAFE=	no

USE_LANGUAGES=		c c++
USE_CXX_FEATURES=	c++11

PLIST_VARS+= native darwin nondarwin
INSTALLATION_DIRS+= include lib share/licenses/zxcvbn-c
.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
TOOL_DEPENDS+= zxcvbn-c>=2.7nb2:../../security/zxcvbn-c
CMAKE_CONFIGURE_ARGS+= -DZXCVBN_NATIVE_DICTGEN=${TOOLBASE}/bin/zxcvbn-dictgen
.else
PLIST.native= yes
INSTALLATION_DIRS+= bin share/zxcvbn
.endif
.if ${OPSYS} == "Darwin"
PLIST.darwin= yes
.else
PLIST.nondarwin= yes
.endif

post-extract:
	${CP} ${FILESDIR}/zxcvbn-dictionary.h ${FILESDIR}/zxcvbn-dictionary-internal.h ${FILESDIR}/zxcvbn-dictionary.c ${WRKSRC}/

do-install:
	${INSTALL_DATA} ${WRKSRC}/zxcvbn.h ${WRKSRC}/zxcvbn-dictionary.h ${DESTDIR}${PREFIX}/include
.if ${OPSYS} == "Darwin"
	${INSTALL_LIB} ${WRKSRC}/${CMAKE_BUILD_DIR}/libzxcvbn.0.dylib ${DESTDIR}${PREFIX}/lib/
	cd ${DESTDIR}${PREFIX}/lib && ${LN} -s libzxcvbn.0.dylib libzxcvbn.dylib
.else
	${INSTALL_LIB} ${WRKSRC}/${CMAKE_BUILD_DIR}/libzxcvbn.so.0 ${DESTDIR}${PREFIX}/lib/
	cd ${DESTDIR}${PREFIX}/lib && ${LN} -s libzxcvbn.so.0 libzxcvbn.so
.endif
.if ${USE_CROSS_COMPILE:Uno:tl} != "yes"
	${INSTALL_PROGRAM} ${WRKSRC}/${CMAKE_BUILD_DIR}/dictgen ${DESTDIR}${PREFIX}/bin/zxcvbn-dictgen
	${INSTALL_DATA} ${WRKSRC}/words-eng_wiki.txt ${WRKSRC}/words-female.txt ${WRKSRC}/words-male.txt ${WRKSRC}/words-passwd.txt ${WRKSRC}/words-surname.txt ${WRKSRC}/words-tv_film.txt ${DESTDIR}${PREFIX}/share/zxcvbn/
.endif
	${INSTALL_DATA} ${WRKSRC}/LICENSE.txt ${DESTDIR}${PREFIX}/share/licenses/zxcvbn-c/LICENSE.txt

.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"

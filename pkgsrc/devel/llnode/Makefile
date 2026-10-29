# $NetBSD$

DISTNAME=	llnode-4.0.0
CATEGORIES=	devel
MASTER_SITES=	${MASTER_SITE_GITHUB:=nodejs/}
GITHUB_TAG=	v${PKGVERSION_NOREV}

HOMEPAGE=	https://github.com/nodejs/llnode/
COMMENT=	LLDB plugin for inspecting Node.js and V8
LICENSE=	mit

USE_LANGUAGES=	c++
USE_CXX_FEATURES=	c++17
NO_CONFIGURE=	yes

.include "../../mk/bsd.prefs.mk"

LLNODE_SOURCES=	constants error llnode llv8 llv8-constants llscan printer node node-constants settings
LLNODE_PLUGIN=	llnode.so
LLNODE_SHARED_FLAGS=	-shared
.if ${OPSYS} == "Darwin"
LLNODE_PLUGIN=	llnode.dylib
LLNODE_SHARED_FLAGS=	-dynamiclib
.endif
PLIST_SUBST+=	LLNODE_PLUGIN=${LLNODE_PLUGIN}

do-build:
	cd ${WRKSRC} && ${CXX} -I${WRKSRC:Q} ${CPPFLAGS} ${CXXFLAGS} -std=c++17 -fPIC ${LLNODE_SHARED_FLAGS} \
	    ${LLNODE_SOURCES:@s@src/${s}.cc@} ${LDFLAGS} -llldb -o ${LLNODE_PLUGIN}

do-install:
	${INSTALL_LIB_DIR} ${DESTDIR}${PREFIX}/lib/lldb/plugins
	${INSTALL_LIB} ${WRKSRC}/${LLNODE_PLUGIN} ${DESTDIR}${PREFIX}/lib/lldb/plugins/${LLNODE_PLUGIN}

.include "../../devel/lldb/buildlink3.mk"
.include "../../devel/rang/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

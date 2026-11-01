# Origin: EmberBSD (AI-assisted); common upstream JavaScript module.
DISTNAME= path-scurry-3.0.0
PKGNAME= node-${DISTNAME}
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/path-scurry/-/
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://www.npmjs.com/package/path-scurry
COMMENT= Fast path walking and resolution with caching
LICENSE= blue-oak-1.0.0
JS_MODULE_NAME= path-scurry
JS_MODULE_DEPENDS+= minipass=node-minipass>=7.1.2:../../devel/node-minipass
JS_MODULE_DEPENDS+= lru-cache=node-lru-cache>=11.0.0:../../devel/node-lru-cache
.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

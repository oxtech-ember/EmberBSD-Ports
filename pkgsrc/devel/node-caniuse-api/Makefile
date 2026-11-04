# Origin: EmberBSD (AI-assisted); common upstream caniuse-api module.
DISTNAME= caniuse-api-4.0.0
PKGNAME= node-caniuse-api-4.0.0
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/caniuse-api/-/
DIST_SUBDIR= node-caniuse-api
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://www.npmjs.com/package/caniuse-api
COMMENT= Common caniuse-api JavaScript module
LICENSE= mit
JS_MODULE_NAME= caniuse-api
JS_MODULE_DEPENDS+= browserslist=node-browserslist>=4.29.5:../../devel/node-browserslist
JS_MODULE_DEPENDS+= caniuse-lite=node-caniuse-lite>=1.0.30001820:../../devel/node-caniuse-lite

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

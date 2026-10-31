# Origin: EmberBSD (AI-assisted); common upstream @jridgewell/trace-mapping module.
DISTNAME= trace-mapping-0.3.31
PKGNAME= node-jridgewell-trace-mapping-0.3.31
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/@jridgewell/trace-mapping/-/
EXTRACT_SUFX= .tgz
DIST_SUBDIR= node-jridgewell-trace-mapping
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://github.com/jridgewell/sourcemaps/tree/main/packages/trace-mapping
COMMENT= Common @jridgewell/trace-mapping JavaScript module
LICENSE= mit
JS_MODULE_NAME= @jridgewell/trace-mapping
JS_MODULE_DEPENDS+= @jridgewell/resolve-uri=node-jridgewell-resolve-uri>=3.1.0:../../devel/node-jridgewell-resolve-uri
JS_MODULE_DEPENDS+= @jridgewell/sourcemap-codec=node-jridgewell-sourcemap-codec>=1.4.14:../../devel/node-jridgewell-sourcemap-codec

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

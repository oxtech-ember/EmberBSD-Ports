# Origin: EmberBSD (AI-assisted); common upstream @jridgewell/gen-mapping module.
DISTNAME= gen-mapping-0.3.13
PKGNAME= node-jridgewell-gen-mapping-0.3.13
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/@jridgewell/gen-mapping/-/
EXTRACT_SUFX= .tgz
DIST_SUBDIR= node-jridgewell-gen-mapping
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://github.com/jridgewell/sourcemaps/tree/main/packages/gen-mapping
COMMENT= Common @jridgewell/gen-mapping JavaScript module
LICENSE= mit
JS_MODULE_NAME= @jridgewell/gen-mapping
JS_MODULE_DEPENDS+= @jridgewell/sourcemap-codec=node-jridgewell-sourcemap-codec>=1.5.0:../../devel/node-jridgewell-sourcemap-codec
JS_MODULE_DEPENDS+= @jridgewell/trace-mapping=node-jridgewell-trace-mapping>=0.3.24:../../devel/node-jridgewell-trace-mapping

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

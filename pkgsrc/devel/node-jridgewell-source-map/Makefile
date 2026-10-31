# Origin: EmberBSD (AI-assisted); common upstream @jridgewell/source-map module.
DISTNAME= source-map-0.3.11
PKGNAME= node-jridgewell-source-map-0.3.11
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/@jridgewell/source-map/-/
EXTRACT_SUFX= .tgz
DIST_SUBDIR= node-jridgewell-source-map
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://github.com/jridgewell/sourcemaps/tree/main/packages/source-map
COMMENT= Common @jridgewell/source-map JavaScript module
LICENSE= mit
JS_MODULE_NAME= @jridgewell/source-map
JS_MODULE_DEPENDS+= @jridgewell/gen-mapping=node-jridgewell-gen-mapping>=0.3.5:../../devel/node-jridgewell-gen-mapping
JS_MODULE_DEPENDS+= @jridgewell/trace-mapping=node-jridgewell-trace-mapping>=0.3.25:../../devel/node-jridgewell-trace-mapping

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

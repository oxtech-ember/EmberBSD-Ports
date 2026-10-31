# Origin: EmberBSD (AI-assisted); common upstream terser module.
DISTNAME= terser-5.51.2
PKGNAME= node-terser-5.51.2
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/terser/-/
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://terser.org
COMMENT= Common terser JavaScript module
LICENSE= 2-clause-bsd
JS_MODULE_NAME= terser
JS_MODULE_DEPENDS+= @jridgewell/source-map=node-jridgewell-source-map>=0.3.3:../../devel/node-jridgewell-source-map
JS_MODULE_DEPENDS+= acorn=node-acorn>=8.15.0:../../devel/node-acorn
JS_MODULE_DEPENDS+= commander=node-commander>=2.20.0:../../devel/node-commander
JS_MODULE_DEPENDS+= source-map-support=node-source-map-support>=0.5.20:../../devel/node-source-map-support

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

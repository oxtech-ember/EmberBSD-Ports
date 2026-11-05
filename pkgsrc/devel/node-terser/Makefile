# Origin: EmberBSD (AI-assisted); common upstream terser module.
DISTNAME= terser-5.51.2
PKGNAME= node-terser-5.51.2
PKGREVISION= 2
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/terser/-/
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://terser.org
COMMENT= Common terser JavaScript module
LICENSE= 2-clause-bsd
JS_MODULE_NAME= terser
REPLACE_NODEJS= bin/terser bin/uglifyjs
JS_MODULE_DEPENDS+= @jridgewell/source-map=node-jridgewell-source-map>=0.3.3:../../devel/node-jridgewell-source-map
JS_MODULE_DEPENDS+= acorn=node-acorn>=8.15.0:../../devel/node-acorn
JS_MODULE_DEPENDS+= commander=node-commander>=15.0.0:../../devel/node-commander

JS_MODULE_PATCH_BACKUPS= bin/terser.orig README.md.orig package.json.orig

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

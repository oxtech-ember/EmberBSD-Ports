# Origin: EmberBSD (AI-assisted); common upstream svgo module.
DISTNAME= svgo-4.1.0
PKGNAME= node-svgo-4.1.0
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/svgo/-/
DIST_SUBDIR= node-svgo
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://www.npmjs.com/package/svgo
COMMENT= Common svgo JavaScript module
LICENSE= mit
JS_MODULE_NAME= svgo
JS_MODULE_DEPENDS+= commander=node-commander>=15.0.0:../../devel/node-commander
JS_MODULE_DEPENDS+= css-select=node-css-select>=7.0.0:../../devel/node-css-select
JS_MODULE_DEPENDS+= css-tree=node-css-tree>=3.2.1:../../devel/node-css-tree
JS_MODULE_DEPENDS+= css-what=node-css-what>=8.0.0:../../devel/node-css-what
JS_MODULE_DEPENDS+= csso=node-csso>=5.0.5:../../devel/node-csso
JS_MODULE_DEPENDS+= picocolors=node-picocolors>=1.1.1:../../devel/node-picocolors
JS_MODULE_DEPENDS+= sax=node-sax>=1.6.1:../../devel/node-sax
REPLACE_NODEJS= bin/svgo.js

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

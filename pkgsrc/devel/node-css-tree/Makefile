# Origin: EmberBSD (AI-assisted); common upstream css-tree module.
DISTNAME= css-tree-3.2.1
PKGNAME= node-css-tree-3.2.1
PKGREVISION= 1
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/css-tree/-/
DIST_SUBDIR= node-css-tree
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://www.npmjs.com/package/css-tree
COMMENT= Common css-tree JavaScript module
LICENSE= mit
JS_MODULE_PATCH_BACKUPS= package.json.orig
JS_MODULE_NAME= css-tree
JS_MODULE_DEPENDS+= mdn-data=node-mdn-data>=2.37.2:../../devel/node-mdn-data
JS_MODULE_DEPENDS+= source-map-js=node-source-map-js>=1.2.2:../../devel/node-source-map-js

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

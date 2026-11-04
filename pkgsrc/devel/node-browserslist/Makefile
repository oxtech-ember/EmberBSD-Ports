# Origin: EmberBSD (AI-assisted); common upstream browserslist module.
DISTNAME= browserslist-4.29.5
PKGNAME= node-browserslist-4.29.5
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/browserslist/-/
DIST_SUBDIR= node-browserslist
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://www.npmjs.com/package/browserslist
COMMENT= Common browserslist JavaScript module
LICENSE= mit
JS_MODULE_NAME= browserslist
JS_MODULE_DEPENDS+= baseline-browser-mapping=node-baseline-browser-mapping>=2.11.35:../../devel/node-baseline-browser-mapping
JS_MODULE_DEPENDS+= caniuse-lite=node-caniuse-lite>=1.0.30001820:../../devel/node-caniuse-lite
JS_MODULE_DEPENDS+= electron-to-chromium=node-electron-to-chromium>=1.5.477:../../devel/node-electron-to-chromium
JS_MODULE_DEPENDS+= node-releases=node-node-releases>=2.0.63:../../devel/node-node-releases
JS_MODULE_DEPENDS+= update-browserslist-db=node-update-browserslist-db>=1.3.4:../../devel/node-update-browserslist-db
REPLACE_NODEJS= cli.js

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

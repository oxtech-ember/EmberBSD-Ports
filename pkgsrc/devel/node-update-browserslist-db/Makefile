# Origin: EmberBSD (AI-assisted); common upstream update-browserslist-db module.
DISTNAME= update-browserslist-db-1.4.0
PKGNAME= node-update-browserslist-db-1.4.0
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/update-browserslist-db/-/
DIST_SUBDIR= node-update-browserslist-db
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://www.npmjs.com/package/update-browserslist-db
COMMENT= Common update-browserslist-db JavaScript module
LICENSE= mit
JS_MODULE_NAME= update-browserslist-db
JS_MODULE_DEPENDS+= escalade=node-escalade>=3.2.0:../../devel/node-escalade
JS_MODULE_DEPENDS+= picocolors=node-picocolors>=1.1.1:../../devel/node-picocolors
JS_MODULE_EXTERNAL_PEERS+= browserslist
REPLACE_NODEJS= cli.js

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

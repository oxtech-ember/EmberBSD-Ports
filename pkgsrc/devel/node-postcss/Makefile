# Origin: EmberBSD (AI-assisted); common upstream postcss module.
DISTNAME= postcss-8.5.33
PKGNAME= node-postcss-8.5.33
PKGREVISION= 1
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/postcss/-/
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://postcss.org/
COMMENT= Common postcss JavaScript module
LICENSE= mit
JS_MODULE_PATCH_BACKUPS= package.json.orig
JS_MODULE_NAME= postcss
JS_MODULE_DEPENDS+= nanoid=node-nanoid>=6.0.2<7:../../devel/node-nanoid
JS_MODULE_DEPENDS+= picocolors=node-picocolors>=1.1.1:../../devel/node-picocolors
JS_MODULE_DEPENDS+= source-map-js=node-source-map-js>=1.2.2:../../devel/node-source-map-js

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

# Origin: EmberBSD (AI-assisted); common upstream postcss-selector-parser module.
DISTNAME= postcss-selector-parser-7.2.1
PKGNAME= node-postcss-selector-parser-7.2.1
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/postcss-selector-parser/-/
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://github.com/postcss/postcss-selector-parser
COMMENT= Common postcss-selector-parser JavaScript module
LICENSE= mit
JS_MODULE_NAME= postcss-selector-parser
JS_MODULE_DEPENDS+= cssesc=node-cssesc>=3.0.0nb2:../../devel/node-cssesc
JS_MODULE_DEPENDS+= util-deprecate=node-util-deprecate>=1.0.2:../../devel/node-util-deprecate

JS_MODULE_PATCH_BACKUPS= package.json.orig

post-extract:
	${CP} ${FILESDIR:Q}/parser-cssesc.js ${WRKSRC:Q}/dist/util/cssesc.js

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

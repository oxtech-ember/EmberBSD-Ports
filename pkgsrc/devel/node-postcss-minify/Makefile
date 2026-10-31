# Origin: EmberBSD (AI-assisted); common upstream postcss-minify module.
DISTNAME= postcss-minify-1.1.0
PKGNAME= node-postcss-minify-1.1.0
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/postcss-minify/-/
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://github.com/jake-low/postcss-minify
COMMENT= Common postcss-minify JavaScript module
LICENSE= mit
JS_MODULE_NAME= postcss-minify
JS_MODULE_DEPENDS+= postcss=node-postcss>=8.0.0:../../devel/node-postcss
JS_MODULE_DEPENDS+= postcss-selector-parser=node-postcss-selector-parser>=6.0.0:../../devel/node-postcss-selector-parser
JS_MODULE_DEPENDS+= postcss-value-parser=node-postcss-value-parser>=4.1.0:../../devel/node-postcss-value-parser

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

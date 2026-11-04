# Origin: EmberBSD (AI-assisted); common upstream postcss-calc module.
DISTNAME= postcss-calc-11.2.3
PKGNAME= node-postcss-calc-11.2.3
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/postcss-calc/-/
DIST_SUBDIR= node-postcss-calc
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://www.npmjs.com/package/postcss-calc
COMMENT= Common postcss-calc JavaScript module
LICENSE= mit
JS_MODULE_NAME= postcss-calc
JS_MODULE_DEPENDS+= @csstools/css-tokenizer=node-csstools-css-tokenizer>=4.0.2:../../devel/node-csstools-css-tokenizer
JS_MODULE_DEPENDS+= postcss=node-postcss>=8.5.32:../../devel/node-postcss

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

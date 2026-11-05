# Origin: EmberBSD (AI-assisted); common upstream cssnano module.
DISTNAME= cssnano-9.9.0
PKGNAME= node-cssnano-9.9.0
PKGREVISION= 1
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/cssnano/-/
DIST_SUBDIR= node-cssnano
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://www.npmjs.com/package/cssnano
COMMENT= Common cssnano JavaScript module
LICENSE= mit
# Exposes the upstream builtin lite preset as cssnano/preset-lite.
JS_MODULE_PATCH_BACKUPS= package.json.orig
JS_MODULE_NAME= cssnano
JS_MODULE_DEPENDS+= @colordx/core=node-colordx-core>=7.3.0:../../devel/node-colordx-core
JS_MODULE_DEPENDS+= @csstools/css-tokenizer=node-csstools-css-tokenizer>=4.0.2:../../devel/node-csstools-css-tokenizer
JS_MODULE_DEPENDS+= browserslist=node-browserslist>=4.29.5:../../devel/node-browserslist
JS_MODULE_DEPENDS+= caniuse-api=node-caniuse-api>=4.0.0:../../devel/node-caniuse-api
JS_MODULE_DEPENDS+= postcss=node-postcss>=8.5.32:../../devel/node-postcss
JS_MODULE_DEPENDS+= postcss-calc=node-postcss-calc>=11.2.3:../../devel/node-postcss-calc

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

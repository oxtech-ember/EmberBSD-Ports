# Origin: EmberBSD (AI-assisted); common upstream css-select module.
DISTNAME= css-select-7.0.0
PKGNAME= node-css-select-7.0.0
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/css-select/-/
DIST_SUBDIR= node-css-select
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://www.npmjs.com/package/css-select
COMMENT= Common css-select JavaScript module
LICENSE= 2-clause-bsd
JS_MODULE_NAME= css-select
JS_MODULE_DEPENDS+= boolbase=node-boolbase>=2.0.0:../../devel/node-boolbase
JS_MODULE_DEPENDS+= css-what=node-css-what>=8.0.0:../../devel/node-css-what
JS_MODULE_DEPENDS+= domhandler=node-domhandler>=6.0.1:../../devel/node-domhandler
JS_MODULE_DEPENDS+= domutils=node-domutils>=4.0.2:../../devel/node-domutils
JS_MODULE_DEPENDS+= nth-check=node-nth-check>=3.0.1:../../devel/node-nth-check

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

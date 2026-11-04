# Origin: EmberBSD (AI-assisted); common upstream csso module.
DISTNAME= csso-5.0.5
PKGNAME= node-csso-5.0.5
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/csso/-/
DIST_SUBDIR= node-csso
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://www.npmjs.com/package/csso
COMMENT= Common csso JavaScript module
LICENSE= mit
JS_MODULE_NAME= csso
JS_MODULE_DEPENDS+= css-tree=node-css-tree>=3.2.1:../../devel/node-css-tree

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

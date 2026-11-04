# Origin: EmberBSD (AI-assisted); common upstream domhandler module.
DISTNAME= domhandler-6.0.1
PKGNAME= node-domhandler-6.0.1
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/domhandler/-/
DIST_SUBDIR= node-domhandler
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://www.npmjs.com/package/domhandler
COMMENT= Common domhandler JavaScript module
LICENSE= 2-clause-bsd
JS_MODULE_NAME= domhandler
JS_MODULE_DEPENDS+= domelementtype=node-domelementtype>=3.0.0:../../devel/node-domelementtype

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

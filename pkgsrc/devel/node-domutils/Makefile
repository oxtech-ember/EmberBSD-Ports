# Origin: EmberBSD (AI-assisted); common upstream domutils module.
DISTNAME= domutils-4.0.2
PKGNAME= node-domutils-4.0.2
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/domutils/-/
DIST_SUBDIR= node-domutils
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://www.npmjs.com/package/domutils
COMMENT= Common domutils JavaScript module
LICENSE= 2-clause-bsd
JS_MODULE_NAME= domutils
JS_MODULE_DEPENDS+= dom-serializer=node-dom-serializer>=3.1.1:../../devel/node-dom-serializer
JS_MODULE_DEPENDS+= domelementtype=node-domelementtype>=3.0.0:../../devel/node-domelementtype
JS_MODULE_DEPENDS+= domhandler=node-domhandler>=6.0.1:../../devel/node-domhandler

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

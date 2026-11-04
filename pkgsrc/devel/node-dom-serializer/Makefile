# Origin: EmberBSD (AI-assisted); common upstream dom-serializer module.
DISTNAME= dom-serializer-3.1.1
PKGNAME= node-dom-serializer-3.1.1
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/dom-serializer/-/
DIST_SUBDIR= node-dom-serializer
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://www.npmjs.com/package/dom-serializer
COMMENT= Common dom-serializer JavaScript module
LICENSE= mit
JS_MODULE_NAME= dom-serializer
JS_MODULE_DEPENDS+= domelementtype=node-domelementtype>=3.0.0:../../devel/node-domelementtype
JS_MODULE_DEPENDS+= domhandler=node-domhandler>=6.0.1:../../devel/node-domhandler
JS_MODULE_DEPENDS+= entities=node-entities>=9.0.0:../../devel/node-entities

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

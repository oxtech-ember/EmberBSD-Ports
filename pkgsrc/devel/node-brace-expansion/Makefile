# Origin: EmberBSD (AI-assisted); common upstream JavaScript module.
DISTNAME= brace-expansion-5.0.12
PKGNAME= node-${DISTNAME}
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/brace-expansion/-/
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://www.npmjs.com/package/brace-expansion
COMMENT= Expand brace expressions
LICENSE= mit
JS_MODULE_NAME= brace-expansion
JS_MODULE_DEPENDS+= balanced-match=node-balanced-match>=5.0.0:../../devel/node-balanced-match
.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

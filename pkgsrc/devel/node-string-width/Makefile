# Origin: EmberBSD (AI-assisted); common upstream string-width JavaScript module.
DISTNAME= string-width-8.3.0
PKGNAME= node-string-width-8.3.0
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/string-width/-/
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://www.npmjs.com/package/string-width
COMMENT= Common string-width JavaScript module
LICENSE= mit
JS_MODULE_NAME= string-width
JS_MODULE_DEPENDS+= strip-ansi=node-strip-ansi>=7.2.0:../../devel/node-strip-ansi
JS_MODULE_DEPENDS+= get-east-asian-width=node-get-east-asian-width>=1.7.0:../../devel/node-get-east-asian-width

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

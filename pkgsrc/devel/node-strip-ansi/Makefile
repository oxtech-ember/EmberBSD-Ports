# Origin: EmberBSD (AI-assisted); common upstream strip-ansi JavaScript module.
DISTNAME= strip-ansi-7.2.0
PKGNAME= node-strip-ansi-7.2.0
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/strip-ansi/-/
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://www.npmjs.com/package/strip-ansi
COMMENT= Common strip-ansi JavaScript module
LICENSE= mit
JS_MODULE_NAME= strip-ansi
JS_MODULE_DEPENDS+= ansi-regex=node-ansi-regex>=6.5.0:../../devel/node-ansi-regex

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

# Origin: EmberBSD (AI-assisted); common upstream lit-html module.
DISTNAME= lit-html-3.3.3
PKGNAME= node-lit-html-3.3.3
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/lit-html/-/
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://github.com/lit/lit
COMMENT= Common lit-html JavaScript module
LICENSE= modified-bsd
JS_MODULE_NAME= lit-html
JS_MODULE_DEPENDS+= @types/trusted-types=node-types-trusted-types>=2.0.7:../../devel/node-types-trusted-types

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

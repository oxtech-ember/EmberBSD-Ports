# Origin: EmberBSD contributors (AI-assisted); common upstream DOMPurify.
DISTNAME= dompurify-3.4.17
PKGNAME= node-dompurify-3.4.17
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/dompurify/-/
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://github.com/cure53/DOMPurify
COMMENT= DOM-based HTML sanitization for JavaScript
LICENSE= mpl-2.0 OR apache-2.0
JS_MODULE_NAME= dompurify
JS_MODULE_DEPENDS+= @types/trusted-types=node-types-trusted-types>=2.0.7:../../devel/node-types-trusted-types

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

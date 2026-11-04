# Origin: EmberBSD contributors (AI-assisted); shared upstream JavaScript module.
DISTNAME= url-parser-1.3.1
PKGNAME= node-ghostery-url-parser-1.3.1
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/@ghostery/url-parser/-/
EXTRACT_SUFX= .tgz
DIST_SUBDIR= node-ghostery-url-parser
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://www.npmjs.com/package/@ghostery/url-parser
COMMENT= Shared @ghostery/url-parser JavaScript module
LICENSE= mpl-2.0
JS_MODULE_NAME= @ghostery/url-parser
JS_MODULE_DEPENDS+= tldts-experimental=node-tldts-experimental>=7.4.19:../../devel/node-tldts-experimental

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

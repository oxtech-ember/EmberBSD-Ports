# Origin: EmberBSD contributors (AI-assisted); shared upstream JavaScript module.
DISTNAME= adblocker-content-2.20.3
PKGNAME= node-ghostery-adblocker-content-2.20.3
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/@ghostery/adblocker-content/-/
EXTRACT_SUFX= .tgz
DIST_SUBDIR= node-ghostery-adblocker-content
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://github.com/ghostery/adblocker#readme
COMMENT= Shared @ghostery/adblocker-content JavaScript module
LICENSE= mpl-2.0
JS_MODULE_NAME= @ghostery/adblocker-content
JS_MODULE_DEPENDS+= @ghostery/adblocker-extended-selectors=node-ghostery-adblocker-extended-selectors>=2.20.3:../../devel/node-ghostery-adblocker-extended-selectors

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

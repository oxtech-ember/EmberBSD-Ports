# Origin: EmberBSD contributors (AI-assisted); shared upstream JavaScript module.
DISTNAME= adblocker-electron-preload-2.20.3
PKGNAME= node-ghostery-adblocker-electron-preload-2.20.3
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/@ghostery/adblocker-electron-preload/-/
EXTRACT_SUFX= .tgz
DIST_SUBDIR= node-ghostery-adblocker-electron-preload
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://github.com/ghostery/adblocker#readme
COMMENT= Shared @ghostery/adblocker-electron-preload JavaScript module
LICENSE= mpl-2.0
JS_MODULE_EXTERNAL_PEERS= electron
JS_MODULE_NAME= @ghostery/adblocker-electron-preload
JS_MODULE_DEPENDS+= @ghostery/adblocker-content=node-ghostery-adblocker-content>=2.20.3:../../devel/node-ghostery-adblocker-content

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

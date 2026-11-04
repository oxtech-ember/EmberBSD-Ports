# Origin: EmberBSD contributors (AI-assisted); shared upstream JavaScript module.
DISTNAME= adblocker-electron-2.20.3
PKGNAME= node-ghostery-adblocker-electron-2.20.3
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/@ghostery/adblocker-electron/-/
EXTRACT_SUFX= .tgz
DIST_SUBDIR= node-ghostery-adblocker-electron
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://github.com/ghostery/adblocker#readme
COMMENT= Shared @ghostery/adblocker-electron JavaScript module
LICENSE= mpl-2.0
JS_MODULE_EXTERNAL_PEERS= electron
JS_MODULE_NAME= @ghostery/adblocker-electron
JS_MODULE_DEPENDS+= @ghostery/adblocker=node-ghostery-adblocker>=2.20.3:../../devel/node-ghostery-adblocker
JS_MODULE_DEPENDS+= @ghostery/adblocker-electron-preload=node-ghostery-adblocker-electron-preload>=2.20.3:../../devel/node-ghostery-adblocker-electron-preload
JS_MODULE_DEPENDS+= tldts-experimental=node-tldts-experimental>=7.4.19:../../devel/node-tldts-experimental

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

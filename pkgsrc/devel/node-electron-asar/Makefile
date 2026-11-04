# Origin: EmberBSD (AI-assisted); common upstream JavaScript module.
DISTNAME= asar-4.3.1
PKGNAME= node-electron-asar-4.3.1
PKGREVISION= 1
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/@electron/asar/-/
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://www.npmjs.com/package/@electron/asar
COMMENT= Electron asar archive creation and extraction
LICENSE= mit
REPLACE_NODEJS= bin/asar.mjs
JS_MODULE_NAME= @electron/asar
JS_MODULE_DEPENDS+= glob=node-glob>=14.0.2:../../devel/node-glob
JS_MODULE_DEPENDS+= minimatch=node-minimatch>=11.0.2:../../devel/node-minimatch
.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

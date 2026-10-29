# Origin: EmberBSD (AI-assisted); common upstream @electron/typescript-definitions module.
DISTNAME= typescript-definitions-10.0.0
PKGNAME= node-electron-typescript-definitions-10.0.0
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/@electron/typescript-definitions/-/
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://www.npmjs.com/package/@electron/typescript-definitions/
COMMENT= Common @electron/typescript-definitions JavaScript module
LICENSE= mit
JS_MODULE_NAME= @electron/typescript-definitions
JS_MODULE_DEPENDS+= @electron/docs-parser=node-electron-docs-parser>=3.0.3:../../devel/node-electron-docs-parser
JS_MODULE_DEPENDS+= @types/node=node-types-node>=26.6.6:../../devel/node-types-node
JS_MODULE_DEPENDS+= chalk=node-chalk>=6.0.1:../../devel/node-chalk
JS_MODULE_DEPENDS+= debug=node-debug>=4.4.3:../../devel/node-debug
JS_MODULE_DEPENDS+= pretty-ms=node-pretty-ms>=10.0.0:../../devel/node-pretty-ms
JS_MODULE_DEPENDS+= yocto-spinner=node-yocto-spinner>=1.2.2:../../devel/node-yocto-spinner

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

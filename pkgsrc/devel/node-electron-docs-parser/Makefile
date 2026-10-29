# Origin: EmberBSD (AI-assisted); common upstream @electron/docs-parser module.
DISTNAME= docs-parser-3.0.3
PKGNAME= node-electron-docs-parser-3.0.3
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/@electron/docs-parser/-/
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://github.com/electron/docs-parser#readme/
COMMENT= Common @electron/docs-parser JavaScript module
LICENSE= mit
JS_MODULE_NAME= @electron/docs-parser
JS_MODULE_DEPENDS+= @types/markdown-it=node-types-markdown-it>=14.2.0:../../devel/node-types-markdown-it
JS_MODULE_DEPENDS+= chai=node-chai>=6.3.0:../../devel/node-chai
JS_MODULE_DEPENDS+= chalk=node-chalk>=6.0.1:../../devel/node-chalk
JS_MODULE_DEPENDS+= lodash.camelcase=node-lodash-camelcase>=4.3.0:../../devel/node-lodash-camelcase
JS_MODULE_DEPENDS+= markdown-it=node-markdown-it>=15.0.3:../../devel/node-markdown-it
JS_MODULE_DEPENDS+= pretty-ms=node-pretty-ms>=10.0.0:../../devel/node-pretty-ms
JS_MODULE_DEPENDS+= yocto-spinner=node-yocto-spinner>=1.2.2:../../devel/node-yocto-spinner

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

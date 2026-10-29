# Origin: EmberBSD (AI-assisted); common upstream lit-element module.
DISTNAME= lit-element-4.2.2
PKGNAME= node-lit-element-4.2.2
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/lit-element/-/
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://github.com/lit/lit
COMMENT= Common lit-element JavaScript module
LICENSE= modified-bsd
JS_MODULE_NAME= lit-element
JS_MODULE_DEPENDS+= lit-html=node-lit-html>=3.3.3:../../devel/node-lit-html
JS_MODULE_DEPENDS+= @lit/reactive-element=node-lit-reactive-element>=2.1.2:../../devel/node-lit-reactive-element
JS_MODULE_DEPENDS+= @lit-labs/ssr-dom-shim=node-lit-ssr-dom-shim>=1.6.0:../../devel/node-lit-ssr-dom-shim

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

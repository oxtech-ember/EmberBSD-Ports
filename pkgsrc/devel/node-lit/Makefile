# Origin: EmberBSD (AI-assisted); common upstream lit module.
DISTNAME= lit-3.3.3
PKGNAME= node-lit-3.3.3
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/lit/-/
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://github.com/lit/lit
COMMENT= Common lit JavaScript module
LICENSE= modified-bsd
JS_MODULE_NAME= lit
JS_MODULE_DEPENDS+= @lit/reactive-element=node-lit-reactive-element>=2.1.2:../../devel/node-lit-reactive-element
JS_MODULE_DEPENDS+= lit-element=node-lit-element>=4.2.2:../../devel/node-lit-element
JS_MODULE_DEPENDS+= lit-html=node-lit-html>=3.3.3:../../devel/node-lit-html

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

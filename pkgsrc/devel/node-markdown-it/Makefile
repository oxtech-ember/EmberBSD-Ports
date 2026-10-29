# Origin: EmberBSD (AI-assisted); common upstream markdown-it module.
DISTNAME= markdown-it-15.0.3
PKGNAME= node-markdown-it-15.0.3
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/markdown-it/-/
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://www.npmjs.com/package/markdown-it/
COMMENT= Common markdown-it JavaScript module
LICENSE= mit
JS_MODULE_NAME= markdown-it
JS_MODULE_DEPENDS+= argparse=node-argparse>=3.0.4:../../devel/node-argparse
JS_MODULE_DEPENDS+= entities=node-entities>=9.0.0:../../devel/node-entities
JS_MODULE_DEPENDS+= linkify-it=node-linkify-it>=6.1.0:../../devel/node-linkify-it
JS_MODULE_DEPENDS+= mdurl=node-mdurl>=2.1.0:../../devel/node-mdurl
JS_MODULE_DEPENDS+= punycode.js=node-punycode-js>=2.3.1:../../devel/node-punycode-js
JS_MODULE_DEPENDS+= uc.micro=node-uc-micro>=3.0.0:../../devel/node-uc-micro

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

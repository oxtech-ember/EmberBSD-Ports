# Origin: EmberBSD (AI-assisted); common upstream @types/node module.
DISTNAME= node-26.6.10
PKGNAME= node-types-node-26.6.10
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/@types/node/-/
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/node
HOMEPAGE= https://github.com/DefinitelyTyped/DefinitelyTyped/tree/master/types/node/
COMMENT= Common @types/node JavaScript module
LICENSE= mit
JS_MODULE_PATCH_BACKUPS= package.json.orig
JS_MODULE_NAME= @types/node
JS_MODULE_DEPENDS+= undici-types=node-undici-types>=8.13.1<8.14:../../devel/node-undici-types

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

# Origin: EmberBSD contributors (AI-assisted); shared upstream JavaScript module.
DISTNAME= smaz-2.2.0
PKGNAME= node-remusao-smaz-2.2.0
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/@remusao/smaz/-/
EXTRACT_SUFX= .tgz
DIST_SUBDIR= node-remusao-smaz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://github.com/remusao/mono#readme
COMMENT= Shared @remusao/smaz JavaScript module
LICENSE= mpl-2.0
JS_MODULE_NAME= @remusao/smaz
JS_MODULE_DEPENDS+= @remusao/smaz-compress=node-remusao-smaz-compress>=2.2.0:../../devel/node-remusao-smaz-compress
JS_MODULE_DEPENDS+= @remusao/smaz-decompress=node-remusao-smaz-decompress>=2.2.0:../../devel/node-remusao-smaz-decompress

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

# Origin: EmberBSD (AI-assisted); common upstream ts-proto-descriptors module.
DISTNAME= ts-proto-descriptors-2.1.0
PKGNAME= node-ts-proto-descriptors-2.1.0
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/ts-proto-descriptors/-/
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://github.com/stephenh/ts-proto
COMMENT= Common ts-proto-descriptors JavaScript module
LICENSE= isc
JS_MODULE_NAME= ts-proto-descriptors
JS_MODULE_DEPENDS+= @bufbuild/protobuf=node-bufbuild-protobuf>=2.16.0:../../devel/node-bufbuild-protobuf

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

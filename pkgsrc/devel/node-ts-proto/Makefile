# Origin: EmberBSD (AI-assisted); common upstream ts-proto module.
DISTNAME= ts-proto-2.18.3
PKGNAME= node-ts-proto-2.18.3
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/ts-proto/-/
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://github.com/stephenh/ts-proto
COMMENT= Common ts-proto JavaScript module
LICENSE= apache-2.0
JS_MODULE_NAME= ts-proto
JS_MODULE_DEPENDS+= @bufbuild/protobuf=node-bufbuild-protobuf>=2.16.0:../../devel/node-bufbuild-protobuf
JS_MODULE_DEPENDS+= case-anything=node-case-anything>=3.1.7:../../devel/node-case-anything
JS_MODULE_DEPENDS+= ts-poet=node-ts-poet>=6.12.0:../../devel/node-ts-poet
JS_MODULE_DEPENDS+= ts-proto-descriptors=node-ts-proto-descriptors>=2.1.0:../../devel/node-ts-proto-descriptors

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

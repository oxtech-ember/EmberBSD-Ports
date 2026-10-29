# Origin: EmberBSD (AI-assisted); common upstream @bufbuild/protobuf module.
DISTNAME= protobuf-2.16.0
PKGNAME= node-bufbuild-protobuf-2.16.0
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/@bufbuild/protobuf/-/
EXTRACT_SUFX= .tgz
DIST_SUBDIR= node-bufbuild-protobuf
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://github.com/bufbuild/protobuf-es
COMMENT= Protocol Buffers runtime for ECMAScript
LICENSE= apache-2.0 AND modified-bsd
JS_MODULE_NAME= @bufbuild/protobuf

post-extract:
	${CP} ${FILESDIR}/LICENSE ${WRKSRC}/LICENSE
	${CP} ${FILESDIR}/NOTICE.protobuf ${WRKSRC}/NOTICE.protobuf

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

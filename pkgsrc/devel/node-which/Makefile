# Origin: EmberBSD (AI-assisted); common upstream which Node module.
DISTNAME= which-7.0.0
PKGNAME= node-${DISTNAME}
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/which/-/
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://github.com/npm/node-which
COMMENT= Find executable files in PATH
LICENSE= isc

JS_MODULE_NAME= which
JS_MODULE_DEPENDS+= isexe=node-isexe>=4.0.0:../../devel/node-isexe
REPLACE_NODEJS+= bin/which.js
.include "../../mk/emberbsd-javascript.mk"

post-install:
	${INSTALL_DATA_DIR} ${DESTDIR:Q}${PREFIX:Q}/bin
	${LN} -s ../lib/node_modules/which/bin/which.js ${DESTDIR:Q}${PREFIX:Q}/bin/node-which

GENERATE_PLIST+= ${ECHO} bin/node-which;
.include "../../mk/bsd.pkg.mk"

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
DEPENDS+= nodejs>=26:../../lang/nodejs
REPLACE_NODEJS+= bin/which.js
.include "../../lang/nodejs/application.mk"
.include "../../mk/emberbsd-javascript.mk"

# Run pkgsrc's interpreter replacement; the common source-only helper normally
# skips configure, but this package also installs an executable script.
.undef NO_CONFIGURE
do-configure:
	${DO_NADA}

post-install:
	${INSTALL_DATA_DIR} ${DESTDIR:Q}${PREFIX:Q}/bin
	${LN} -s ../lib/node_modules/which/bin/which.js ${DESTDIR:Q}${PREFIX:Q}/bin/node-which

GENERATE_PLIST+= ${ECHO} bin/node-which;
.include "../../mk/bsd.pkg.mk"

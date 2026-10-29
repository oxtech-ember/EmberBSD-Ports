# Origin: EmberBSD (AI-assisted); common upstream Oxc AST type definitions.
DISTNAME= types-0.156.0
PKGNAME= node-oxc-project-types-0.156.0
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/@oxc-project/types/-/
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://oxc.rs/
COMMENT= Common TypeScript definitions for Oxc AST nodes
LICENSE= mit
JS_MODULE_NAME= @oxc-project/types
TEST_DEPENDS+= typescript-[0-9]*:../../lang/typescript

do-test:
	${MKDIR} ${WRKDIR}/types-smoke/node_modules/@oxc-project
	${RM} -f ${WRKDIR}/types-smoke/node_modules/@oxc-project/types
	${LN} -s ${WRKSRC:Q} ${WRKDIR}/types-smoke/node_modules/@oxc-project/types
	${CP} ${FILESDIR}/smoke.mts ${WRKDIR}/types-smoke/smoke.mts
	${PREFIX}/bin/node ${PREFIX}/lib/node_modules/typescript/bin/tsc --noEmit --strict \
	    --module Node16 --moduleResolution Node16 --target ES2022 ${WRKDIR}/types-smoke/smoke.mts

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

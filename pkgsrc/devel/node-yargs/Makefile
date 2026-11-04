# Origin: EmberBSD (AI-assisted); common upstream yargs JavaScript module.
DISTNAME= yargs-18.2.0
PKGNAME= node-yargs-18.2.0
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/yargs/-/
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://www.npmjs.com/package/yargs
COMMENT= Common yargs JavaScript module
LICENSE= mit
JS_MODULE_NAME= yargs
JS_MODULE_DEPENDS+= y18n=node-y18n>=5.0.8:../../devel/node-y18n
JS_MODULE_DEPENDS+= cliui=node-cliui>=9.0.1:../../devel/node-cliui
JS_MODULE_DEPENDS+= escalade=node-escalade>=3.2.0:../../devel/node-escalade
JS_MODULE_DEPENDS+= string-width=node-string-width>=8.3.0:../../devel/node-string-width
JS_MODULE_DEPENDS+= yargs-parser=node-yargs-parser>=22.0.0:../../devel/node-yargs-parser
JS_MODULE_DEPENDS+= get-caller-file=node-get-caller-file>=2.0.5:../../devel/node-get-caller-file

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

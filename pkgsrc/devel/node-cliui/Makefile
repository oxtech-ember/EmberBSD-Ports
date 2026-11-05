# Origin: EmberBSD (AI-assisted); common upstream cliui JavaScript module.
DISTNAME= cliui-9.0.1
PKGNAME= node-cliui-9.0.1
PKGREVISION= 1
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/cliui/-/
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://www.npmjs.com/package/cliui
COMMENT= Common cliui JavaScript module
LICENSE= isc
JS_MODULE_PATCH_BACKUPS= package.json.orig
JS_MODULE_NAME= cliui
JS_MODULE_DEPENDS+= wrap-ansi=node-wrap-ansi>=10.0.2:../../devel/node-wrap-ansi
JS_MODULE_DEPENDS+= strip-ansi=node-strip-ansi>=7.2.0:../../devel/node-strip-ansi
JS_MODULE_DEPENDS+= string-width=node-string-width>=8.3.0:../../devel/node-string-width

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

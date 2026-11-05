# Origin: EmberBSD (AI-assisted); common upstream wrap-ansi JavaScript module.
DISTNAME= wrap-ansi-10.0.2
PKGNAME= node-wrap-ansi-10.0.2
PKGREVISION= 1
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/wrap-ansi/-/
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://www.npmjs.com/package/wrap-ansi
COMMENT= Common wrap-ansi JavaScript module
LICENSE= mit
JS_MODULE_PATCH_BACKUPS= package.json.orig
JS_MODULE_NAME= wrap-ansi
JS_MODULE_DEPENDS+= ansi-styles=node-ansi-styles>=7.0.0:../../devel/node-ansi-styles
JS_MODULE_DEPENDS+= string-width=node-string-width>=8.3.0:../../devel/node-string-width

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

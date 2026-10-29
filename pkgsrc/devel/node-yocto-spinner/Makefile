# Origin: EmberBSD (AI-assisted); common upstream yocto-spinner module.
DISTNAME= yocto-spinner-1.2.2
PKGNAME= node-yocto-spinner-1.2.2
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/yocto-spinner/-/
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://www.npmjs.com/package/yocto-spinner/
COMMENT= Common yocto-spinner JavaScript module
LICENSE= mit
JS_MODULE_NAME= yocto-spinner
JS_MODULE_DEPENDS+= yoctocolors=node-yoctocolors>=2.2.0:../../devel/node-yoctocolors

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

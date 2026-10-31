# Origin: EmberBSD (AI-assisted); common upstream source-map-support module.
DISTNAME= source-map-support-0.5.21
PKGNAME= node-source-map-support-0.5.21
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/source-map-support/-/
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://github.com/evanw/node-source-map-support
COMMENT= Common source-map-support JavaScript module
LICENSE= mit
JS_MODULE_NAME= source-map-support
JS_MODULE_DEPENDS+= buffer-from=node-buffer-from>=1.0.0:../../devel/node-buffer-from
JS_MODULE_DEPENDS+= source-map=node-source-map>=0.6.0:../../devel/node-source-map

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

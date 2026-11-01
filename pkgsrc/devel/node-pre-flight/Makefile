# Origin: EmberBSD (AI-assisted); common upstream JavaScript module.
DISTNAME= pre-flight-2.0.0
PKGNAME= node-${DISTNAME}
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/pre-flight/-/
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://www.npmjs.com/package/pre-flight
COMMENT= Check that installed npm dependencies satisfy package.json
LICENSE= mit
JS_MODULE_NAME= pre-flight
JS_MODULE_DEPENDS+= chalk=node-chalk>=5.3.0:../../devel/node-chalk
JS_MODULE_DEPENDS+= semver=node-semver>=7.6.3:../../devel/node-semver
.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

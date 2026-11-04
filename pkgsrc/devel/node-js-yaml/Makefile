# Origin: EmberBSD (AI-assisted); common upstream js-yaml JavaScript module.
DISTNAME= js-yaml-5.5.0
PKGNAME= node-js-yaml-5.5.0
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/js-yaml/-/
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://www.npmjs.com/package/js-yaml
COMMENT= Common js-yaml JavaScript module
LICENSE= mit
JS_MODULE_NAME= js-yaml
JS_MODULE_DEPENDS+= argparse=node-argparse>=3.0.4:../../devel/node-argparse
REPLACE_NODEJS+= bin/js-yaml.mjs

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

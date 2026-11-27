# Origin: EmberBSD (AI-assisted); common upstream JavaScript module.
DISTNAME= glob-14.0.6
PKGNAME= node-${DISTNAME}
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/glob/-/
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://www.npmjs.com/package/glob
COMMENT= Filesystem globbing for Node.js
LICENSE= blue-oak-1.0.0
JS_MODULE_NAME= glob

JS_MODULE_DEPENDS+= minipass=node-minipass>=7.1.3:../../devel/node-minipass
JS_MODULE_DEPENDS+= minimatch=node-minimatch>=11.0.5:../../devel/node-minimatch
JS_MODULE_DEPENDS+= path-scurry=node-path-scurry>=3.0.0:../../devel/node-path-scurry
.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD" && ${MACHINE_ARCH} == "aarch64"
PKGREVISION=	1	# Reissue the withdrawn AArch64 package.
.endif
.include "../../mk/bsd.pkg.mk"

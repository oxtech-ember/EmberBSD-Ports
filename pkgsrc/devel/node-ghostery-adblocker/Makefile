# Origin: EmberBSD contributors (AI-assisted); shared upstream JavaScript module.
DISTNAME= adblocker-2.20.3
PKGNAME= node-ghostery-adblocker-2.20.3
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/@ghostery/adblocker/-/
EXTRACT_SUFX= .tgz
GHOSTERY_SOURCE_REV= 6f0610bf5eec1f31c4975ce0e707cdf47023e5b5
GHOSTERY_RESOURCE= ghostery-resources-6f0610bf.json
DISTFILES= ${DISTNAME}${EXTRACT_SUFX} ${GHOSTERY_RESOURCE}
SITES.${GHOSTERY_RESOURCE}= -https://raw.githubusercontent.com/ghostery/adblocker/${GHOSTERY_SOURCE_REV}/packages/adblocker/assets/ublock-origin/resources.json
EXTRACT_ONLY= ${DISTNAME}${EXTRACT_SUFX}
INSTALLATION_DIRS+= share/ghostery-adblocker
DIST_SUBDIR= node-ghostery-adblocker
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://github.com/ghostery/adblocker#readme
COMMENT= Shared @ghostery/adblocker JavaScript module
LICENSE= mpl-2.0
JS_MODULE_NAME= @ghostery/adblocker
JS_MODULE_DEPENDS+= @ghostery/adblocker-content=node-ghostery-adblocker-content>=2.20.3:../../devel/node-ghostery-adblocker-content
JS_MODULE_DEPENDS+= @ghostery/adblocker-extended-selectors=node-ghostery-adblocker-extended-selectors>=2.20.3:../../devel/node-ghostery-adblocker-extended-selectors
JS_MODULE_DEPENDS+= @ghostery/url-parser=node-ghostery-url-parser>=1.3.1:../../devel/node-ghostery-url-parser
JS_MODULE_DEPENDS+= @remusao/guess-url-type=node-remusao-guess-url-type>=2.1.0:../../devel/node-remusao-guess-url-type
JS_MODULE_DEPENDS+= @remusao/small=node-remusao-small>=2.1.0:../../devel/node-remusao-small
JS_MODULE_DEPENDS+= @remusao/smaz=node-remusao-smaz>=2.2.0:../../devel/node-remusao-smaz
JS_MODULE_DEPENDS+= tldts-experimental=node-tldts-experimental>=7.4.19:../../devel/node-tldts-experimental

post-install:
	${INSTALL_DATA} ${DISTDIR:Q}/${DIST_SUBDIR:Q}/${GHOSTERY_RESOURCE:Q} ${DESTDIR:Q}${PREFIX:Q}/share/ghostery-adblocker/resources.json

GENERATE_PLIST+= ${ECHO} share/ghostery-adblocker/resources.json;
.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

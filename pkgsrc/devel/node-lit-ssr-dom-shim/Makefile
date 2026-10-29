# Origin: EmberBSD (AI-assisted); common upstream @lit-labs/ssr-dom-shim module.
DISTNAME= ssr-dom-shim-1.6.0
PKGNAME= node-lit-ssr-dom-shim-1.6.0
CATEGORIES= devel
MASTER_SITES= https://registry.npmjs.org/@lit-labs/ssr-dom-shim/-/
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/package
HOMEPAGE= https://github.com/lit/lit
COMMENT= Common @lit-labs/ssr-dom-shim JavaScript module
LICENSE= modified-bsd
JS_MODULE_NAME= @lit-labs/ssr-dom-shim

# LICENSE from the upstream @lit-labs/ssr-dom-shim@1.6.0 tag; npm omits it.
post-extract:
	${CP} ${FILESDIR:Q}/LICENSE ${WRKSRC:Q}/LICENSE

.include "../../mk/emberbsd-javascript.mk"
.include "../../mk/bsd.pkg.mk"

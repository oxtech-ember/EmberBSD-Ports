# Blanc v1.25.0 source package on the separately packaged Electron runtime.
# Upstream release commit: ff55d5948f5c71e802ba2ac464659ef96e055ca9.
# Intended pkgsrc paths are www/blanc and devel/electron44.
# This recipe and its local portability patches were prepared with AI assistance.

DISTNAME=	blanc-1.25.0
PKGREVISION=	1
CATEGORIES=	www
BLANC_SOURCE=	v1.25.0${EXTRACT_SUFX}
MASTER_SITES=	https://github.com/bnfy/blanc/archive/refs/tags/
BLANC_NPM_DISTFILES= \
	adblocker-2.18.2.tgz \
	adblocker-content-2.18.2.tgz \
	adblocker-electron-2.18.2.tgz \
	adblocker-electron-preload-2.18.2.tgz \
	adblocker-extended-selectors-2.18.2.tgz \
	argparse-2.0.1.tgz \
	asar-4.3.0.tgz \
	balanced-match-4.0.4.tgz \
	brace-expansion-5.0.12.tgz \
	builder-util-runtime-9.7.0.tgz \
	debug-4.4.3.tgz \
	electron-updater-6.8.9.tgz \
	fs-extra-10.1.0.tgz \
	glob-13.0.6.tgz \
	graceful-fs-4.2.11.tgz \
	guess-url-type-2.1.0.tgz \
	js-yaml-4.3.2.tgz \
	jsonfile-6.2.1.tgz \
	lazy-val-1.0.5.tgz \
	lodash.escaperegexp-4.1.2.tgz \
	lodash.isequal-4.5.0.tgz \
	lru-cache-11.5.2.tgz \
	minimatch-10.2.5.tgz \
	minipass-7.1.3.tgz \
	ms-2.1.3.tgz \
	path-scurry-2.0.2.tgz \
	sax-1.6.0.tgz \
	sdk-0.5.0.tgz \
	sdk-core-0.5.0.tgz \
	semver-7.7.4.tgz \
	small-2.1.0.tgz \
	smaz-2.2.0.tgz \
	smaz-compress-2.2.0.tgz \
	smaz-decompress-2.2.0.tgz \
	tiny-typed-emitter-2.1.0.tgz \
	tldts-core-7.4.10.tgz \
	tldts-experimental-7.4.10.tgz \
	trie-2.1.0.tgz \
	universalify-2.0.1.tgz \
	url-parser-1.3.1.tgz
DISTFILES=	${BLANC_SOURCE} ${BLANC_NPM_DISTFILES}
DIST_SUBDIR=	e12-electron
EXTRACT_ONLY=	${BLANC_SOURCE}

SITES.adblocker-2.18.2.tgz=	https://registry.npmjs.org/@ghostery/adblocker/-/
SITES.adblocker-content-2.18.2.tgz=	https://registry.npmjs.org/@ghostery/adblocker-content/-/
SITES.adblocker-electron-2.18.2.tgz=	https://registry.npmjs.org/@ghostery/adblocker-electron/-/
SITES.adblocker-electron-preload-2.18.2.tgz=	https://registry.npmjs.org/@ghostery/adblocker-electron-preload/-/
SITES.adblocker-extended-selectors-2.18.2.tgz=	https://registry.npmjs.org/@ghostery/adblocker-extended-selectors/-/
SITES.argparse-2.0.1.tgz=	https://registry.npmjs.org/argparse/-/
SITES.asar-4.3.0.tgz=	https://registry.npmjs.org/@electron/asar/-/
SITES.balanced-match-4.0.4.tgz=	https://registry.npmjs.org/balanced-match/-/
SITES.brace-expansion-5.0.12.tgz=	https://registry.npmjs.org/brace-expansion/-/
SITES.builder-util-runtime-9.7.0.tgz=	https://registry.npmjs.org/builder-util-runtime/-/
SITES.debug-4.4.3.tgz=	https://registry.npmjs.org/debug/-/
SITES.electron-updater-6.8.9.tgz=	https://registry.npmjs.org/electron-updater/-/
SITES.fs-extra-10.1.0.tgz=	https://registry.npmjs.org/fs-extra/-/
SITES.glob-13.0.6.tgz=	https://registry.npmjs.org/glob/-/
SITES.graceful-fs-4.2.11.tgz=	https://registry.npmjs.org/graceful-fs/-/
SITES.guess-url-type-2.1.0.tgz=	https://registry.npmjs.org/@remusao/guess-url-type/-/
SITES.js-yaml-4.3.2.tgz=	https://registry.npmjs.org/js-yaml/-/
SITES.jsonfile-6.2.1.tgz=	https://registry.npmjs.org/jsonfile/-/
SITES.lazy-val-1.0.5.tgz=	https://registry.npmjs.org/lazy-val/-/
SITES.lodash.escaperegexp-4.1.2.tgz=	https://registry.npmjs.org/lodash.escaperegexp/-/
SITES.lodash.isequal-4.5.0.tgz=	https://registry.npmjs.org/lodash.isequal/-/
SITES.lru-cache-11.5.2.tgz=	https://registry.npmjs.org/lru-cache/-/
SITES.minimatch-10.2.5.tgz=	https://registry.npmjs.org/minimatch/-/
SITES.minipass-7.1.3.tgz=	https://registry.npmjs.org/minipass/-/
SITES.ms-2.1.3.tgz=	https://registry.npmjs.org/ms/-/
SITES.path-scurry-2.0.2.tgz=	https://registry.npmjs.org/path-scurry/-/
SITES.sax-1.6.0.tgz=	https://registry.npmjs.org/sax/-/
SITES.sdk-0.5.0.tgz=	https://registry.npmjs.org/@1password/sdk/-/
SITES.sdk-core-0.5.0.tgz=	https://registry.npmjs.org/@1password/sdk-core/-/
SITES.semver-7.7.4.tgz=	https://registry.npmjs.org/semver/-/
SITES.small-2.1.0.tgz=	https://registry.npmjs.org/@remusao/small/-/
SITES.smaz-2.2.0.tgz=	https://registry.npmjs.org/@remusao/smaz/-/
SITES.smaz-compress-2.2.0.tgz=	https://registry.npmjs.org/@remusao/smaz-compress/-/
SITES.smaz-decompress-2.2.0.tgz=	https://registry.npmjs.org/@remusao/smaz-decompress/-/
SITES.tiny-typed-emitter-2.1.0.tgz=	https://registry.npmjs.org/tiny-typed-emitter/-/
SITES.tldts-core-7.4.10.tgz=	https://registry.npmjs.org/tldts-core/-/
SITES.tldts-experimental-7.4.10.tgz=	https://registry.npmjs.org/tldts-experimental/-/
SITES.trie-2.1.0.tgz=	https://registry.npmjs.org/@remusao/trie/-/
SITES.universalify-2.0.1.tgz=	https://registry.npmjs.org/universalify/-/
SITES.url-parser-1.3.1.tgz=	https://registry.npmjs.org/@ghostery/url-parser/-/

MAINTAINER=	oxtech-ember@users.noreply.github.com
HOMEPAGE=	https://github.com/bnfy/blanc
COMMENT=	Desktop browser application for the system Electron runtime
LICENSE=	mit AND cc-by-sa-v3.0 AND ofl-v1.1 AND isc AND mpl-2.0 AND python-software-foundation AND blueoak-1.0.0
# Blue Oak is not in the pinned pkgsrc license catalog. Keep its exact text
# with the installed notices; users must explicitly accept blueoak-1.0.0.

# The unchanged Blanc identity artwork and trademarks are not redistributable.
RESTRICTED=	Blanc identity artwork and marks may not identify a modified build.
NO_SRC_ON_FTP=	${RESTRICTED}
NO_SRC_ON_CDROM=	${RESTRICTED}
NO_BIN_ON_FTP=	${RESTRICTED}
NO_BIN_ON_CDROM=	${RESTRICTED}

BLANC_ELECTRON_RUNTIME_VERSION=	44.9.3
BLANC_ELECTRON_PKGDIR=	../../devel/electron44
BLANC_ELECTRON_DEPENDS=	electron>=${BLANC_ELECTRON_RUNTIME_VERSION}<44.9.4:${BLANC_ELECTRON_PKGDIR}
BLANC_NODE_VERSION=	26.13.0
BLANC_SOURCE_SHA256=	b241d6b135b0fab5839f5dea6f64fafbdefa4f213b46ffa4a2f78820cb880971
BLANC_SOURCE_FILES_SHA256=	89932ab7cb1966bf5a00fe114945acad393f14493d0bcd3157c43d5c697a20c7
BLANC_NPM_MANIFEST_SHA256=	f4b8db0e788ff5be1c448440d9c94cd4a543241fa8d8b44d7e10ce2ff0c68462
BUILD_HOST_NODE=	${EMBERBSD_HOST_NODE}
BUILD_HOST_PYTHON=	${EMBERBSD_CROSS_BUILD_PYTHON}
DEPENDS+=	${BLANC_ELECTRON_DEPENDS}
INSTALLATION_DIRS+=	bin lib/blanc share/applications share/doc/blanc

.include "../../mk/bsd.prefs.mk"

# Fetch and checksum need no selected build tools. Validate each tool at its
# first consuming phase, using pkgsrc's public phase hooks.
.PHONY: blanc-check-source-tools blanc-check-build-tools
pre-extract: blanc-check-source-tools
pre-build pre-test: blanc-check-build-tools

blanc-check-source-tools:
.if !defined(EMBERBSD_SDK_SOURCE) || empty(EMBERBSD_SDK_SOURCE:M/*) || !exists(${EMBERBSD_SDK_SOURCE}/src/emberbsd_sdk/__init__.py)
	${FAIL_MSG} "Blanc requires an explicit EMBERBSD_SDK_SOURCE API 1 source"
.endif
.if !defined(EMBERBSD_CROSS_BUILD_PYTHON) || empty(EMBERBSD_CROSS_BUILD_PYTHON:M/*) || !exists(${EMBERBSD_CROSS_BUILD_PYTHON})
	${FAIL_MSG} "Blanc requires the selected host Python 3.15+ in EMBERBSD_CROSS_BUILD_PYTHON"
.endif

blanc-check-build-tools: blanc-check-source-tools
.if !defined(EMBERBSD_HOST_NODE) || empty(EMBERBSD_HOST_NODE:M/*) || !exists(${EMBERBSD_HOST_NODE})
	${FAIL_MSG} "Blanc requires the selected host Node.js 26.13.0 in EMBERBSD_HOST_NODE"
.endif
.if !defined(EMBERBSD_HOST_PREFIX) || empty(EMBERBSD_HOST_PREFIX:M/*) || !exists(${EMBERBSD_HOST_PREFIX})
	${FAIL_MSG} "Blanc requires the selected native EMBERBSD_HOST_PREFIX"
.endif

do-extract: blanc-check-source-tools
	${MKDIR} ${WRKDIR:Q}
	${BUILD_HOST_PYTHON:Q} -B -I -S ${FILESDIR:Q}/build-blanc.py \
	    --sdk-source ${EMBERBSD_SDK_SOURCE:Q} extract \
	    --source ${WRKSRC:Q} \
	    --archive ${DISTDIR:Q}/${DIST_SUBDIR:Q}/${BLANC_SOURCE:Q} \
	    --source-archive-sha256 ${BLANC_SOURCE_SHA256:Q} \
	    --source-files-sha256 ${BLANC_SOURCE_FILES_SHA256:Q}

do-build: blanc-check-build-tools
	${RM} -rf ${WRKDIR:Q}/runtime-node-modules ${WRKDIR:Q}/asar-tools \
	    ${WRKDIR:Q}/app-stage ${WRKDIR:Q}/seed-inputs ${WRKDIR:Q}/electron-shim \
	    ${WRKDIR:Q}/tmp ${WRKDIR:Q}/home ${WRKDIR:Q}/app.asar ${WRKDIR:Q}/SBOM.json
	${MKDIR} ${WRKDIR:Q}/tmp ${WRKDIR:Q}/home
	${BUILD_HOST_PYTHON:Q} -B -I -S ${FILESDIR:Q}/build-blanc.py \
	    --sdk-source ${EMBERBSD_SDK_SOURCE:Q} build \
	    --source ${WRKSRC:Q} --distdir ${DISTDIR:Q}/${DIST_SUBDIR:Q} \
	    --work ${WRKDIR:Q} --node ${BUILD_HOST_NODE:Q} \
	    --host-prefix ${EMBERBSD_HOST_PREFIX:Q} \
	    --source-archive-sha256 ${BLANC_SOURCE_SHA256:Q} \
	    --source-files-sha256 ${BLANC_SOURCE_FILES_SHA256:Q} \
	    --electron-version ${BLANC_ELECTRON_RUNTIME_VERSION:Q} \
	    --electron-package-path ${BLANC_ELECTRON_PKGDIR:Q} \
	    --electron-depends ${BLANC_ELECTRON_DEPENDS:Q}

do-test: blanc-check-build-tools
	${BUILD_HOST_PYTHON:Q} -B -I -S ${FILESDIR:Q}/build-blanc.py \
	    --sdk-source ${EMBERBSD_SDK_SOURCE:Q} test \
	    --source ${WRKSRC:Q} --distdir ${DISTDIR:Q}/${DIST_SUBDIR:Q} \
	    --work ${WRKDIR:Q} --node ${BUILD_HOST_NODE:Q} \
	    --host-prefix ${EMBERBSD_HOST_PREFIX:Q} \
	    --source-archive-sha256 ${BLANC_SOURCE_SHA256:Q} \
	    --source-files-sha256 ${BLANC_SOURCE_FILES_SHA256:Q} \
	    --electron-version ${BLANC_ELECTRON_RUNTIME_VERSION:Q} \
	    --electron-package-path ${BLANC_ELECTRON_PKGDIR:Q} \
	    --electron-depends ${BLANC_ELECTRON_DEPENDS:Q}

do-install:
	${INSTALL_DATA} ${WRKDIR:Q}/app.asar ${DESTDIR:Q}${PREFIX:Q}/lib/blanc/app.asar
	${INSTALL_DATA} ${WRKSRC:Q}/LICENSE ${WRKSRC:Q}/ASSET-LICENSE.md \
	    ${WRKSRC:Q}/THIRD-PARTY-NOTICES.md ${WRKDIR:Q}/SBOM.json \
	    ${FILESDIR:Q}/blueoak-1.0.0.txt \
	    ${DESTDIR:Q}${PREFIX:Q}/share/doc/blanc/
	${SED} 's|@PREFIX@|${PREFIX}|g' ${FILESDIR:Q}/blanc.sh > ${WRKDIR:Q}/blanc
	${INSTALL_SCRIPT} ${WRKDIR:Q}/blanc ${DESTDIR:Q}${PREFIX:Q}/bin/blanc
	${SED} 's|@PREFIX@|${PREFIX}|g' ${FILESDIR:Q}/blanc.desktop > ${WRKDIR:Q}/blanc.desktop
	${INSTALL_DATA} ${WRKDIR:Q}/blanc.desktop ${DESTDIR:Q}${PREFIX:Q}/share/applications/blanc.desktop

.include "../../sysutils/desktop-file-utils/desktopdb.mk"
.include "../../mk/bsd.pkg.mk"

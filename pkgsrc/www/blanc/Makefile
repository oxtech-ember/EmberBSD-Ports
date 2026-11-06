# Blanc v1.46.0 source package on the separately packaged Electron runtime.
# Upstream release commit: 6479ed3a314e4fd6219b8de1598bacffa78b4d7c.
# Shared pkgsrc owners are www/blanc and devel/electron44.
# This recipe and its local portability patches were prepared with AI assistance.

DISTNAME=	blanc-1.46.0
PKGNAME=	ember-browser-1.46.0
PKGREVISION=	2
CATEGORIES=	www
BLANC_SOURCE=	v1.46.0${EXTRACT_SUFX}
MASTER_SITES=	https://github.com/bnfy/blanc/archive/refs/tags/
DISTFILES=	${BLANC_SOURCE}
DIST_SUBDIR=	e12-electron
EXTRACT_ONLY=	${BLANC_SOURCE}
BLANC_ASAR_MIN_VERSION=	4.3.1

MAINTAINER=	oxtech-ember@users.noreply.github.com
HOMEPAGE=	https://github.com/bnfy/blanc
COMMENT=	Ember Browser, based on Blanc and system Electron
TOOL_DEPENDS+=	node-ghostery-adblocker-electron>=2.20.3:../../devel/node-ghostery-adblocker-electron
TOOL_DEPENDS+=	node-readability>=0.6.0:../../devel/node-readability
TOOL_DEPENDS+=	node-dompurify>=3.4.17:../../devel/node-dompurify
TOOL_DEPENDS+=	node-electron-asar>=${BLANC_ASAR_MIN_VERSION}:../../devel/node-electron-asar
TOOL_DEPENDS+=	node-semver>=7.8.5:../../devel/node-semver
LICENSE=	mit AND apache-2.0 AND cc-by-sa-v3.0 AND ofl-v1.1 AND isc AND mpl-2.0

# The unfiltered upstream archive includes reserved and third-party imagery.
NO_SRC_ON_FTP=	Unfiltered upstream archive includes reserved identity artwork and third-party imagery.
NO_SRC_ON_CDROM=	${NO_SRC_ON_FTP}

BLANC_ELECTRON_RUNTIME_VERSION=	45.2.1
BLANC_ELECTRON_MIN_PKG_VERSION=	45.2.1nb2
BLANC_ELECTRON_PKGDIR=	../../devel/electron44
BLANC_ELECTRON_DEPENDS=	electron>=${BLANC_ELECTRON_MIN_PKG_VERSION}<45.2.2:${BLANC_ELECTRON_PKGDIR}
BLANC_NODE_VERSION=	26.13.0
BLANC_SOURCE_SHA256=	cdba222bb036eee845716371d7d7aa3f66369bbfd4a40d11951e47d3f6a1f166
BLANC_SOURCE_FILES_SHA256=	9dcf9dde9e6eefb843a864a67a58455c0d19a8f77c9a1ef7e5747d9773d9a768
BUILD_HOST_NODE=	${EMBERBSD_HOST_NODE}
BUILD_HOST_PYTHON=	${EMBERBSD_CROSS_BUILD_PYTHON}
DEPENDS+=	${BLANC_ELECTRON_DEPENDS}
INSTALLATION_DIRS+=	bin lib/ember-browser share/applications share/doc/ember-browser share/icons/hicolor/scalable/apps

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
	    --projection ${_PKGSRCDIR:Q}/mk/emberbsd-js-projection.py \
	    --source-archive-sha256 ${BLANC_SOURCE_SHA256:Q} \
	    --source-files-sha256 ${BLANC_SOURCE_FILES_SHA256:Q} \
	    --asar-min-version ${BLANC_ASAR_MIN_VERSION:Q} \
	    --electron-version ${BLANC_ELECTRON_RUNTIME_VERSION:Q} \
	    --electron-package-path ${BLANC_ELECTRON_PKGDIR:Q} \
	    --electron-depends ${BLANC_ELECTRON_DEPENDS:Q}

do-test: blanc-check-build-tools
	${BUILD_HOST_PYTHON:Q} -B -I -S ${FILESDIR:Q}/build-blanc.py \
	    --sdk-source ${EMBERBSD_SDK_SOURCE:Q} test \
	    --source ${WRKSRC:Q} --distdir ${DISTDIR:Q}/${DIST_SUBDIR:Q} \
	    --work ${WRKDIR:Q} --node ${BUILD_HOST_NODE:Q} \
	    --host-prefix ${EMBERBSD_HOST_PREFIX:Q} \
	    --projection ${_PKGSRCDIR:Q}/mk/emberbsd-js-projection.py \
	    --source-archive-sha256 ${BLANC_SOURCE_SHA256:Q} \
	    --source-files-sha256 ${BLANC_SOURCE_FILES_SHA256:Q} \
	    --asar-min-version ${BLANC_ASAR_MIN_VERSION:Q} \
	    --electron-version ${BLANC_ELECTRON_RUNTIME_VERSION:Q} \
	    --electron-package-path ${BLANC_ELECTRON_PKGDIR:Q} \
	    --electron-depends ${BLANC_ELECTRON_DEPENDS:Q}

do-install:
	${INSTALL_DATA} ${FILESDIR:Q}/ember-browser.svg ${DESTDIR:Q}${PREFIX:Q}/share/icons/hicolor/scalable/apps/org.emberbsd.browser.svg
	${INSTALL_DATA} ${WRKDIR:Q}/app.asar ${DESTDIR:Q}${PREFIX:Q}/lib/ember-browser/app.asar
	${INSTALL_DATA} ${WRKSRC:Q}/LICENSE ${WRKSRC:Q}/ASSET-LICENSE.md \
	    ${WRKSRC:Q}/THIRD-PARTY-NOTICES.md ${WRKSRC:Q}/TRADEMARKS.md ${WRKDIR:Q}/SBOM.json \
	    ${DESTDIR:Q}${PREFIX:Q}/share/doc/ember-browser/
	${SED} 's|@PREFIX@|${PREFIX}|g' ${FILESDIR:Q}/blanc.sh > ${WRKDIR:Q}/ember-browser
	${INSTALL_SCRIPT} ${WRKDIR:Q}/ember-browser ${DESTDIR:Q}${PREFIX:Q}/bin/ember-browser
	${SED} 's|@PREFIX@|${PREFIX}|g' ${FILESDIR:Q}/blanc.desktop > ${WRKDIR:Q}/org.emberbsd.browser.desktop
	${INSTALL_DATA} ${WRKDIR:Q}/org.emberbsd.browser.desktop ${DESTDIR:Q}${PREFIX:Q}/share/applications/org.emberbsd.browser.desktop

.include "../../sysutils/desktop-file-utils/desktopdb.mk"
.include "../../mk/bsd.pkg.mk"

# EmberBSD probe: Electron 44.9.3 runtime for NetBSD/aarch64.
# Not buildable yet; see ../README.md for the plan and boundaries.

DISTNAME=	electron-44.9.3
PKGREVISION=	1
CATEGORIES=	devel
MASTER_SITES=	https://github.com/electron/electron/archive/refs/tags/
DISTFILES=	v44.9.3${EXTRACT_SUFX}
DIST_SUBDIR=	e12-electron
PATCH_STRIP=	-p1

CHROMIUM_VERSION=	152.0.7977.167
# Backport Electron PR55162 in the recipe-local security patch below.
NODE_VERSION=		24.22.1
DISTFILES+=	node-v${NODE_VERSION}.tar.xz
SITES.node-v${NODE_VERSION}.tar.xz=	https://nodejs.org/dist/v${NODE_VERSION}/

MAINTAINER=	oxtech-ember@users.noreply.github.com
HOMEPAGE=	https://www.electronjs.org/
COMMENT=	Build cross-platform desktop apps with JavaScript, HTML, and CSS
LICENSE=	mit AND mpl-2.0 AND modified-bsd

# Cross-build with the shared Clang/LLVM SDK and matching EmberBSD runtime.
# Select GCC only through an explicit platform profile.
USE_CROSS_COMPILE=	yes
USE_LANGUAGES=		c c++
USE_TOOLS+=		pkg-config

# Host Node runs the Electron JS toolchain; products are target artifacts.
BUILD_HOST_NODE=	${EMBERBSD_HOST_NODE}
BUILD_HOST_NPM=		${EMBERBSD_HOST_NPM}

# Electron v44.9.3 pins Chromium ${CHROMIUM_VERSION} in DEPS.  The Chromium
# source comes from the pinned gclient dependency graph, not a mismatched
# chromium-browser-official tarball.  Keep its DEPS revision and the NetBSD
# overlay revision in the build receipt.
# TODO(build): apply the NetBSD patch set to this exact Chromium pin, add the
# Electron target GN configuration, build with the selected SDK, and package
# the runtime.

.include "../../mk/bsd.pkg.mk"

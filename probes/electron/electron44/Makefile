# EmberBSD probe: Electron 44.5.1 runtime for NetBSD/aarch64.
# Not buildable yet; see ../README.md for the plan and boundaries.

DISTNAME=	electron-44.9.0
CATEGORIES=	devel
MASTER_SITES=	https://github.com/electron/electron/archive/refs/tags/
DISTFILES=	v44.9.0${EXTRACT_SUFX}
DIST_SUBDIR=	e12-electron

CHROMIUM_VERSION=	152.0.7977.82
NODE_VERSION=		24.21.0
DISTFILES+=	chromium-${CHROMIUM_VERSION}.tar.xz
SITES.chromium-${CHROMIUM_VERSION}.tar.xz=	https://commondatastorage.googleapis.com/chromium-browser-official/
DISTFILES+=	node-v${NODE_VERSION}.tar.xz
SITES.node-v${NODE_VERSION}.tar.xz=	https://nodejs.org/dist/v${NODE_VERSION}/

MAINTAINER=	oxtech-ember@users.noreply.github.com
HOMEPAGE=	https://www.electronjs.org/
COMMENT=	Build cross-platform desktop apps with JavaScript, HTML, and CSS
LICENSE=	mit AND mpl-2.0 AND BSD-3-clause

# Owner decision 2026-10-16: cross build with the shared GCC16 toolchain
# and the shared EmberBSD sysroot, like every other EmberBSD profile.
USE_CROSS_COMPILE=	yes
USE_LANGUAGES=		c c++
USE_TOOLS+=		pkg-config

# Host Node runs the Electron JS toolchain; products are target artifacts.
BUILD_HOST_NODE=	${EMBERBSD_HOST_NODE}
BUILD_HOST_NPM=		${EMBERBSD_HOST_NPM}

# TODO(build): GN args for cross aarch64 (target_os/target_cpu, is_clang,
# use_sysroot from the cross profile), chromium-nb patch series, Electron
# patch series re-targeted .130 -> .82, node host build, packaging.
# No silent stubs: each step lands with its real command and check.

.include "../../mk/bsd.pkg.mk"

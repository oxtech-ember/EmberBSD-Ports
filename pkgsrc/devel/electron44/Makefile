# Electron 45.2.1 runtime for NetBSD.
# Target execution, GUI and hardware acceptance remain pending.

DISTNAME=	electron-45.2.1
PKGREVISION=	1
CATEGORIES=	devel
# The source owner prepares the complete pinned workspace separately.  The
# controller verifies it; no prebuilt distribution ZIP is a build input.
DISTFILES=
# The selected workspace already contains the owner's complete patch series.
# Keep the pkgsrc scratch directory separate from that reusable source tree.
WRKSRC=		${WRKDIR}

CHROMIUM_VERSION=	156.0.8078.75

MAINTAINER=	oxtech-ember@users.noreply.github.com
HOMEPAGE=	https://www.electronjs.org/
COMMENT=	Build cross-platform desktop apps with JavaScript, HTML, and CSS
LICENSE=	mit AND mpl-2.0 AND modified-bsd

# Cross-build with the shared Clang/LLVM SDK and matching EmberBSD runtime.
# Select GCC only through an explicit platform profile.
USE_CROSS_COMPILE=	yes
USE_LANGUAGES=		c c++
USE_TOOLS+=		pkg-config

# Inputs and producer work are selected explicitly in producer.mk.
# The prepared source owner applies patches before the controller verifies it.
# Override the pkgsrc patch target so recipe-local patches are not applied twice.
do-patch:
	@${DO_NADA}

.include "../../mk/bsd.prefs.mk"
.include "producer.mk"

.include "runtime-dependencies.mk"
.include "../../mk/bsd.pkg.mk"

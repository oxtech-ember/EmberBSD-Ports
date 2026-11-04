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

# Shared native JavaScript providers selected by the Electron producer.
TOOL_DEPENDS+= node-electron-asar>=4.3.1:../../devel/node-electron-asar
TOOL_DEPENDS+= node-electron-docs-parser>=3.0.3:../../devel/node-electron-docs-parser
TOOL_DEPENDS+= node-electron-typescript-definitions>=10.0.0:../../devel/node-electron-typescript-definitions
TOOL_DEPENDS+= node-types-node>=26.6.6:../../devel/node-types-node
TOOL_DEPENDS+= node-pre-flight>=2.0.0:../../devel/node-pre-flight
TOOL_DEPENDS+= rolldown>=1.2.16:../../devel/rolldown
TOOL_DEPENDS+= node-semver>=7.8.5:../../devel/node-semver
TOOL_DEPENDS+= typescript>=7.0.2:../../lang/typescript
TOOL_DEPENDS+= node-primer-octicons>=19.42.0:../../devel/node-primer-octicons
TOOL_DEPENDS+= node-postcss-minify>=1.2.0:../../devel/node-postcss-minify

# Inputs and producer work are selected explicitly in producer.mk.
# The prepared source owner applies patches before the controller verifies it.
# Override the pkgsrc patch target so recipe-local patches are not applied twice.
do-patch:
	@${DO_NADA}

.include "../../mk/bsd.prefs.mk"
.include "producer.mk"

.include "runtime-dependencies.mk"
.include "../../mk/bsd.pkg.mk"

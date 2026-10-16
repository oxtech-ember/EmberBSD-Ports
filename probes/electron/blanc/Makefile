# EmberBSD probe: Blanc browser package on the Electron runtime.
# Not installable until the electron44 runtime port builds.

DISTNAME=	blanc-1.25.0
CATEGORIES=	www
MASTER_SITES=	https://github.com/bnfy/blanc/archive/refs/tags/
DISTFILES=	v1.25.0${EXTRACT_SUFX}
DIST_SUBDIR=	e12-electron

MAINTAINER=	oxtech-ember@users.noreply.github.com
HOMEPAGE=	https://github.com/bnfy/blanc
COMMENT=	Desktop browser with a minimal Island interface (Electron)
LICENSE=	mit

DEPENDS+=	electron44>=44.5.1:../../probes/electron/electron44

# Install plan: the application JS tree and bundled, hash-verified filter
# lists go to ${PREFIX}/share/blanc; a wrapper script starts the system
# electron runtime with that resource root. electron-builder is not used.
# The npm dependency tree is prepared in the fetch phase with host Node.

# TODO(build): offline npm mirror for Blanc dependencies, PLIST, wrapper,
# desktop file, upstream unit checks that run without a display.

.include "../../mk/bsd.pkg.mk"

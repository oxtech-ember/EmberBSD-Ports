# Origin: EmberBSD (AI-assisted). First port; Union from Plasma 6.8 needs it.

DISTNAME=	cxx-rust-cssparser-1.1.0
PKGREVISION=	1
CATEGORIES=	devel
MASTER_SITES=	${MASTER_SITE_GITHUB:=KDE/}
GITHUB_TAG=	v1.1.0
EXTRACT_SUFX=	.tar.gz

# Offline crate sources generated on the host with `cargo vendor` from
# rust/Cargo.lock. Regenerate this archive when the crate set changes.
DISTFILES=	cxx-rust-cssparser-1.1.0.tar.gz cxx-rust-cssparser-vendor-1.1.0.tar.gz

HOMEPAGE=	https://invent.kde.org/libraries/cxx-rust-cssparser
COMMENT=	C++ CSS parsing API implemented through the Rust cssparser crate
LICENSE=	modified-bsd AND gnu-lgpl-v2.1 AND cc0-1.0-universal

.include "../../mk/bsd.prefs.mk"

USE_CMAKE=	yes
USE_LANGUAGES=	c c++
USE_TOOLS+=	pkg-config ar
CMAKE_CONFIGURE_ARGS+= -DBUILD_TESTING=OFF
CMAKE_CONFIGURE_ARGS+= -DBUILD_EXAMPLES=OFF

post-extract:
	${MV} ${WRKDIR}/vendor ${WRKSRC}/rust/vendor

.include "cross.mk"

.include "../../devel/extra-cmake-modules/buildlink3.mk"
.include "../../mk/pthread.buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

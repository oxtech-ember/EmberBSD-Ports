# Origin: EmberBSD (AI-assisted). First port; Union from Plasma 6.8 needs it.

DISTNAME=	cxx-rust-cssparser-1.1.0
PKGREVISION=	2
CATEGORIES=	devel
MASTER_SITES=	${MASTER_SITE_GITHUB:=KDE/}
GITHUB_TAG=	v1.1.0
EXTRACT_SUFX=	.tar.gz

# Offline crate sources generated on the host with `cargo vendor` from
# rust/Cargo.lock. Regenerate this archive when the crate set changes.
_EMBER_CSS_VENDOR_DISTFILE= cxx-rust-cssparser-vendor-1.1.0-r1.tar
DISTFILES=	cxx-rust-cssparser-1.1.0.tar.gz ${_EMBER_CSS_VENDOR_DISTFILE}
# This archive is locally derived, not an upstream HTTP release asset.
SITES.${_EMBER_CSS_VENDOR_DISTFILE}=

HOMEPAGE=	https://invent.kde.org/libraries/cxx-rust-cssparser
COMMENT=	C++ CSS parsing API implemented through the Rust cssparser crate
LICENSE=	modified-bsd AND gnu-lgpl-v2.1 AND cc0-1.0-universal

.include "../../mk/bsd.prefs.mk"

USE_CMAKE=	yes
USE_LANGUAGES=	c c++
USE_TOOLS+=	pkg-config ar
CMAKE_CONFIGURE_ARGS+= -DBUILD_TESTING=OFF
CMAKE_CONFIGURE_ARGS+= -DBUILD_EXAMPLES=OFF

pre-fetch:
	@${TEST} -f ${DISTDIR:Q}/${_EMBER_CSS_VENDOR_DISTFILE:Q} || { \
		${ERROR_MSG} "Prepare ${_EMBER_CSS_VENDOR_DISTFILE} with files/vendor.rb and copy the verified archive into DISTDIR; see README.md."; exit 1; }
	@expected=$$(${AWK} '$$1 == "SHA512" && $$2 == "(${_EMBER_CSS_VENDOR_DISTFILE})" {print $$4}' ${DISTINFO_FILE:Q}); \
	actual=$$(${DIGEST} SHA512 ${DISTDIR:Q}/${_EMBER_CSS_VENDOR_DISTFILE:Q} | ${AWK} '{print $$NF}'); \
	${TEST} -n "$$expected" && ${TEST} "$$actual" = "$$expected" || { \
		${ERROR_MSG} "Derived CSS parser vendor checksum mismatch."; exit 1; }

post-extract:
	${MV} ${WRKDIR}/vendor ${WRKSRC}/rust/vendor

.include "cross.mk"

.include "../../devel/extra-cmake-modules/buildlink3.mk"
.include "../../mk/pthread.buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

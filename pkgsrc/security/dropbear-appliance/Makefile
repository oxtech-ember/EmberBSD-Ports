# EmberBSD static server variant of the shared Dropbear source.
FILESDIR=	${.CURDIR:H}/dropbear/files
PATCHDIR=	${.CURDIR:H}/dropbear/patches
DISTINFO_FILE=	${.CURDIR:H}/dropbear/distinfo
PLIST_SRC=	${.CURDIR:H}/dropbear/PLIST
DESCR_SRC=	${.CURDIR:H}/dropbear/DESCR

.include "../../security/dropbear/Makefile.common"

PKGNAME=	${DISTNAME:S/^dropbear-/dropbear-appliance-/}
CONFIGURE_ARGS+=	--enable-static
CPPFLAGS+=	-DROPBEAR_APPLIANCE_PROFILE
CONFLICTS+=	dropbear-[0-9]*

.include "../../mk/bsd.pkg.mk"

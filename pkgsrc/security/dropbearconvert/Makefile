# Convert existing OpenSSH and Dropbear private keys for provisioning.
PATCHDIR=	${.CURDIR:H}/dropbear/patches
DISTINFO_FILE=	${.CURDIR:H}/dropbear/distinfo

DROPBEAR_CONVERT_ONLY=	yes
.include "../../security/dropbear/Makefile.common"

PKGNAME=	${DISTNAME:S/^dropbear-/dropbearconvert-/}
COMMENT=	Convert between OpenSSH and Dropbear key formats
CONFLICTS+=	dropbear-[0-9]* dropbear-appliance-[0-9]*

CONFIGURE_ARGS+=	--disable-zlib
MAKE_FLAGS+=		PROGRAMS=dropbearconvert

.include "../../mk/bsd.pkg.mk"

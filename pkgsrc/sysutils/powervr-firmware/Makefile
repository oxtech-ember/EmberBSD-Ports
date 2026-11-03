# Origin: EmberBSD; shared unmodified PowerVR Rogue firmware inputs.
DISTNAME=	powervr-firmware-1.1.6976702
CATEGORIES=	sysutils

HOMEPAGE=	https://gitlab.freedesktop.org/imagination/linux-firmware/
COMMENT=	PowerVR Rogue firmware for selected GE8300 and BXM profiles
LICENSE=	powervr-firmware-license
LICENSE_FILE=	${WRKSRC}/LICENSE.powervr

POWERVR_REVISION=	8a58f81883f7be458daa34e418cc4079f995b279
POWERVR_FILES=		rogue_22.102.54.38_v1.fw rogue_36.56.104.183_v1.fw
POWERVR_SOURCE=		https://gitlab.freedesktop.org/api/v4/projects/imagination%2Flinux-firmware/repository/files
DIST_SUBDIR=		powervr-firmware/${POWERVR_REVISION}
DISTFILES=		${POWERVR_FILES} LICENSE.powervr WHENCE
.for image in ${POWERVR_FILES}
SITES.${image}=		-${POWERVR_SOURCE}/powervr%2F${image}/raw?ref=${POWERVR_REVISION}
.endfor
SITES.LICENSE.powervr=	-${POWERVR_SOURCE}/LICENSE.powervr/raw?ref=${POWERVR_REVISION}
SITES.WHENCE=		-${POWERVR_SOURCE}/WHENCE/raw?ref=${POWERVR_REVISION}

WRKSRC=		${WRKDIR}
EXTRACT_ONLY=
NO_CONFIGURE=	yes
NO_BUILD=	yes
NO_ARCH=	yes

INSTALLATION_DIRS=	libdata/firmware/powervr share/doc/powervr-firmware

do-extract:
	${MKDIR} ${WRKSRC}/powervr
.for image in ${POWERVR_FILES}
	${CP} ${DISTDIR}/${DIST_SUBDIR}/${image} ${WRKSRC}/powervr/
.endfor
	${CP} ${DISTDIR}/${DIST_SUBDIR}/LICENSE.powervr ${WRKSRC}/
	${CP} ${DISTDIR}/${DIST_SUBDIR}/WHENCE ${WRKSRC}/

do-install:
.for image in ${POWERVR_FILES}
	${INSTALL_DATA} ${WRKSRC}/powervr/${image} \
	    ${DESTDIR}${PREFIX}/libdata/firmware/powervr/
.endfor
	${INSTALL_DATA} ${WRKSRC}/LICENSE.powervr \
	    ${DESTDIR}${PREFIX}/libdata/firmware/powervr/
	${INSTALL_DATA} ${WRKSRC}/WHENCE \
	    ${DESTDIR}${PREFIX}/share/doc/powervr-firmware/

.include "../../mk/bsd.pkg.mk"

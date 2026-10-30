# $NetBSD: opensbi-version.mk,v 1.1 2024/06/17 11:20:32 skrll Exp $

OPENSBI_DEFAULT_VERSION=	1.9

OPENSBI_VERSION?=		${OPENSBI_DEFAULT_VERSION}
.if ${OPENSBI_VERSION} != ${OPENSBI_DEFAULT_VERSION}
PKG_FAIL_REASON+=	"Only the common OpenSBI ${OPENSBI_DEFAULT_VERSION} is supported"
.endif

.if ${OPENSBI_VERSION} != ${OPENSBI_DEFAULT_VERSION}
DISTINFO_FILE?=	${.CURDIR}/../../sysutils/opensbi/distinfo-${OPENSBI_VERSION}
PATCHDIR?=	${.CURDIR}/../../sysutils/opensbi/patches-${OPENSBI_VERSION}
.else
PATCHDIR?=	${.CURDIR}/../../sysutils/opensbi/patches
.endif

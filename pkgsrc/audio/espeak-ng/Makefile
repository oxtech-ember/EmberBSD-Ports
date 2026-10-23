# $NetBSD: Makefile,v 1.9 2026/09/02 19:00:46 wiz Exp $

DISTNAME=	espeak-ng-1.52.0
PKGREVISION=	5
CATEGORIES=	audio
MASTER_SITES=	${MASTER_SITE_GITHUB:=espeak-ng/}
GITHUB_TAG=	${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/espeak-ng/espeak-ng/
COMMENT=	Open source speech synthesizer
LICENSE=	gnu-gpl-v3 AND apache-2.0 AND 2-clause-bsd AND unicode

DEPENDS+=	mbrola-[0-9]*:../../audio/mbrola

USE_TOOLS+=	autoconf automake autoreconf gmake
GNU_CONFIGURE=	yes
USE_LIBTOOL=	yes
USE_LANGUAGES=	c c++

TEST_TARGET=	check

.include "../../mk/bsd.prefs.mk"

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
.if empty(EMBERBSD_ESPEAK_HOST:M/*) || !empty(EMBERBSD_ESPEAK_HOST:C/[A-Za-z0-9_.\/-]//g) || !exists(${EMBERBSD_ESPEAK_HOST})
PKG_FAIL_REASON+= "EMBERBSD_ESPEAK_HOST must name the verified native eSpeak NG 1.52.0 generator"
.endif
MAKE_FLAGS+= ESPEAK_GEN=${EMBERBSD_ESPEAK_HOST:Q}
pre-configure: emberbsd-espeak-host-check
.PHONY: emberbsd-espeak-host-check
emberbsd-espeak-host-check:
	${RUN}${EMBERBSD_ESPEAK_HOST} --version > ${WRKDIR}/.espeak-host-version 2>&1
	${RUN}${GREP} '^eSpeak NG text-to-speech: 1[.]52[.]0 ' ${WRKDIR}/.espeak-host-version
.endif


# -D_NETBSD_SOURCE for mkstemp in /usr/include/stdlib.h
.if ${OPSYS} == "NetBSD"
CFLAGS+=	-D_NETBSD_SOURCE
.endif

CFLAGS.SunOS+=	-D_LARGEFILE64_SOURCE -D__EXTENSIONS__

PKGCONFIG_OVERRIDE+=	espeak-ng.pc.in

# Makefile.am: error: required file './AUTHORS' not found
pre-configure:
	set -e; cd ${WRKSRC} && touch AUTHORS NEWS && autoreconf -fi

.include "options.mk"
.include "../../audio/pcaudiolib/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

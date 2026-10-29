# $NetBSD: Makefile,v 1.9 2026/09/02 19:00:46 wiz Exp $

DISTNAME=	espeak-ng-1.52.0
PKGREVISION=	6
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
# Origin: EmberBSD (AI-assisted). The target espeak-ng cannot compile the
# phoneme and dictionary data on the build host. The native data compiler
# comes from audio/espeak-ng-generator and must be the same release.
ESPEAK_GENERATOR_VERSION=	${PKGVERSION_NOREV}
TOOL_DEPENDS+=	espeak-ng-generator-${ESPEAK_GENERATOR_VERSION}{,nb[0-9]*}:../../audio/espeak-ng-generator
ESPEAK_GENERATOR=	${TOOLBASE}/libexec/espeak-ng-generator
MAKE_FLAGS+=	ESPEAK_GEN=${ESPEAK_GENERATOR:Q}
pre-configure: emberbsd-espeak-generator-check
.PHONY: emberbsd-espeak-generator-check
emberbsd-espeak-generator-check:
	${RUN}${ESPEAK_GENERATOR:Q} --version > ${WRKDIR}/.espeak-generator-version 2>&1
	${RUN}${GREP} '^eSpeak NG text-to-speech: ${ESPEAK_GENERATOR_VERSION:S/./[.]/g} ' \
	    ${WRKDIR}/.espeak-generator-version
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

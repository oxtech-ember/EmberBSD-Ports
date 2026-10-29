# $NetBSD$
# Origin: EmberBSD (AI-assisted). Native eSpeak NG data compiler for cross builds.

DISTNAME=	espeak-ng-1.52.0
PKGNAME=	${DISTNAME:S/espeak-ng/espeak-ng-generator/}
CATEGORIES=	audio
MASTER_SITES=	${MASTER_SITE_GITHUB:=espeak-ng/}
GITHUB_PROJECT=	espeak-ng
GITHUB_TAG=	${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/espeak-ng/espeak-ng/
COMMENT=	Native eSpeak NG data compiler for audio/espeak-ng cross builds
LICENSE=	gnu-gpl-v3 AND apache-2.0 AND 2-clause-bsd AND unicode

# The cross recipe selects this exact version. Its compiled phoneme and
# dictionary tables must come from the same eSpeak NG release.
ESPEAK_GENERATOR_VERSION=	1.52.0

# The generated tables contain native integer fields. They match the
# aarch64 target only for an accepted host ABI.
ONLY_FOR_PLATFORM=	Darwin-*-aarch64

USE_TOOLS+=	autoconf automake autoreconf gmake
GNU_CONFIGURE=	yes
USE_LANGUAGES=	c c++
CONFIGURE_ARGS+=	--without-pcaudiolib --without-sonic --with-mbrola
CONFIGURE_ARGS+=	--disable-shared --disable-rpath
BUILD_TARGET=	src/espeak-ng
INSTALLATION_DIRS=	libexec

.include "../../mk/bsd.prefs.mk"

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
PKG_FAIL_REASON+=	"${PKGNAME} is a build-host tool; build it natively"
.endif

# PKGVERSION_NOREV is not defined yet while this file is parsed.
.if "${DISTNAME:S/^espeak-ng-//}" != "${ESPEAK_GENERATOR_VERSION}"
PKG_FAIL_REASON+=	"${PKGNAME} must be eSpeak NG ${ESPEAK_GENERATOR_VERSION}"
.endif

# The autotools build omits upstream's macOS endian compatibility include.
# Expose only endian.h: the compatibility wctype.h breaks libc++.
ESPEAK_COMPAT=	${WRKDIR}/compat
CPPFLAGS+=	-I${ESPEAK_COMPAT}

# Makefile.am: error: required file './AUTHORS' not found
pre-configure:
	${MKDIR} ${ESPEAK_COMPAT}
	${LN} -sf ${WRKSRC}/src/include/compat/endian.h ${ESPEAK_COMPAT}/endian.h
	set -e; cd ${WRKSRC} && touch AUTHORS NEWS && autoreconf -fi

post-build:
	${RUN}${WRKSRC}/src/espeak-ng --version > ${WRKDIR}/.espeak-generator-version 2>&1
	${RUN}${GREP} '^eSpeak NG text-to-speech: ${ESPEAK_GENERATOR_VERSION:S/./[.]/g} ' \
	    ${WRKDIR}/.espeak-generator-version

do-install:
	${INSTALL_PROGRAM} ${WRKSRC}/src/espeak-ng \
	    ${DESTDIR}${PREFIX}/libexec/espeak-ng-generator

.include "../../mk/bsd.pkg.mk"

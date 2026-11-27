# $NetBSD$
# Origin: EmberBSD (AI-assisted). Native eSpeak NG data compiler for cross builds.

DISTNAME=	espeak-ng-1.52.0
PKGNAME=	${DISTNAME:S/espeak-ng/espeak-ng-generator/}
PKGREVISION=	2
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
# The generator compiles the same source as audio/espeak-ng. Use its
# distfile record and its portability patches.
DISTINFO_FILE=	${.CURDIR}/../espeak-ng/distinfo
PATCHDIR=	${.CURDIR}/../espeak-ng/patches

# The generated tables contain native integer fields. They match the
# target only for an accepted host ABI: Darwin aarch64 for aarch64, and an
# EmberBSD amd64 host for the amd64 target, which has the same ABI.
ONLY_FOR_PLATFORM=	Darwin-*-aarch64 NetBSD-*-x86_64

USE_TOOLS+=	autoconf automake autoreconf gmake
GNU_CONFIGURE=	yes
USE_LANGUAGES=	c c++
CONFIGURE_ARGS+=	--without-pcaudiolib --without-sonic --with-mbrola
CONFIGURE_ARGS+=	--disable-shared --disable-rpath
BUILD_TARGET=	src/espeak-ng
MAKE_FLAGS+=	DATADIR=espeak-ng-data
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
# Expose only endian.h: the compatibility wctype.h breaks libc++. EmberBSD
# has its own endian.h.
.if ${OPSYS} == "Darwin"
ESPEAK_COMPAT=	${WRKDIR}/compat
CPPFLAGS+=	-I${ESPEAK_COMPAT}
.endif
# The BSD declarations of the EmberBSD headers that eSpeak NG uses.
CPPFLAGS.NetBSD+=	-D_NETBSD_SOURCE

# Makefile.am: error: required file './AUTHORS' not found
pre-configure:
.if ${OPSYS} == "Darwin"
	${MKDIR} ${ESPEAK_COMPAT}
	${LN} -sf ${WRKSRC}/src/include/compat/endian.h ${ESPEAK_COMPAT}/endian.h
.endif
	set -e; cd ${WRKSRC} && touch AUTHORS NEWS && autoreconf -fi

post-build:
	${RUN}${WRKSRC}/src/espeak-ng --version > ${WRKDIR}/.espeak-generator-version 2>&1
	${RUN}${GREP} '^eSpeak NG text-to-speech: ${ESPEAK_GENERATOR_VERSION:S/./[.]/g} ' \
	    ${WRKDIR}/.espeak-generator-version

do-install:
	${INSTALL_PROGRAM} ${WRKSRC}/src/espeak-ng \
	    ${DESTDIR}${PREFIX}/libexec/espeak-ng-generator

.include "../../mk/bsd.pkg.mk"

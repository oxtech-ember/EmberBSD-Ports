# $NetBSD: Makefile,v 1.13 2024/08/06 12:38:50 wiz Exp $

DISTNAME=	libinotify
PKGNAME=	${DISTNAME}-0.0.${GITHUB_TAG}
PKGREVISION=	1
CATEGORIES=	devel
MASTER_SITES=	${MASTER_SITE_GITHUB:=libinotify-kqueue/}
GITHUB_PROJECT=	libinotify-kqueue
GITHUB_TAG=	20240724

MAINTAINER=	me@dmitrymatveev.co.uk
#HOMEPAGE=	http://dmitrymatveev.co.uk/gsoc11
COMMENT=	Inotify emulation library for *BSDs
LICENSE=	mit

GNU_CONFIGURE=	YES
USE_LIBTOOL=	yes
USE_LANGUAGES=	c c++17
USE_TOOLS+=	autoconf automake autoreconf

.include "../../mk/compiler.mk"

# configure runs kqueue and path-descriptor test programs, which a cross
# build cannot execute. These are the results of the EmberBSD target probe
# (probes/plasma-mobile/toolkit/tests/libinotify) on NetBSD 11.0 aarch64
# and amd64. The amd64 measurement ran on GENERIC_AMD_DRM build #7
# on 2026-11-04; probe source SHA256 046fc882c2bb16e109afecd533c7634de50ed2e3d7195a90dc6bb69c09ced731.
# Other cross targets fail in configure until they are measured.
.if ${USE_CROSS_COMPILE:tl} == "yes" && (${MACHINE_PLATFORM} == "NetBSD-11.0-aarch64" || \
    ${MACHINE_PLATFORM} == "NetBSD-11.0-x86_64")
CONFIGURE_ENV+=	ember_cv_note_extend_to=yes ember_cv_note_extend_from=no
CONFIGURE_ENV+=	ember_cv_o_path=no ember_cv_o_empty_path=no ember_cv_at_empty_path=no
.endif

# Avoid error due to use of ATOMIC_VAR_INIT.
.if ${CC_VERSION:Mclang-1[5-9].*}
CFLAGS+=	-Wno-deprecated-pragma
.endif

TEST_TARGET=	test

NOT_FOR_PLATFORM+=	SunOS-*-* Linux-*-*

pre-configure:
	cd ${WRKSRC} && autoreconf -fvi

.include "../../mk/pthread.buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

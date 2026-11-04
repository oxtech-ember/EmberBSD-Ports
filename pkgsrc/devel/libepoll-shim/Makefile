# $NetBSD: Makefile,v 1.13 2024/08/25 06:18:35 wiz Exp $

DISTNAME=	${GITHUB_PROJECT}-0.0.20240608
PKGNAME=	lib${DISTNAME}
PKGREVISION=	1
CATEGORIES=	devel
MASTER_SITES=	${MASTER_SITE_GITHUB:=jiixyj/}
GITHUB_PROJECT=	epoll-shim
GITHUB_TAG=	v${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/jiixyj/epoll-shim
COMMENT=	Small epoll implemented using kevent
LICENSE=	mit

USE_LANGUAGES=	c c++

CMAKE_CONFIGURE_ARGS+=	-DBUILD_TESTING=OFF
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_PKGCONFIGDIR=${PREFIX}/lib/pkgconfig

# re-defines read(2) itself
FORTIFY_SUPPORTED=	no

.include "../../mk/bsd.prefs.mk"

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# Recorded target results of the upstream zero-timeout oneshot kqueue probe
# (profiles/common-graphics/cross/wayland.md). Platforms without a record need an explicit measurement;
# an explicit MAKECONF value still overrides a record.
_EMBERBSD_EPOLL_ZERO_TIMER_RECORD.aarch64= 1
_EMBERBSD_EPOLL_ZERO_TIMER_RECORD.x86_64= 1
.if !defined(EMBERBSD_EPOLL_ZERO_TIMER_EXITCODE) && \
    ${CROSS_OPSYS:U} == "NetBSD" && !empty(CROSS_OS_VERSION:M11.*) && \
    defined(_EMBERBSD_EPOLL_ZERO_TIMER_RECORD.${CROSS_MACHINE_ARCH:U})
EMBERBSD_EPOLL_ZERO_TIMER_EXITCODE= ${_EMBERBSD_EPOLL_ZERO_TIMER_RECORD.${CROSS_MACHINE_ARCH}}
.endif
.if "${EMBERBSD_EPOLL_ZERO_TIMER_EXITCODE:U}" != "0" && "${EMBERBSD_EPOLL_ZERO_TIMER_EXITCODE:U}" != "1"
PKG_FAIL_REASON+= "Cross libepoll-shim requires the measured EMBERBSD_EPOLL_ZERO_TIMER_EXITCODE=0 or 1"
.else
CMAKE_CONFIGURE_ARGS+= -DALLOWS_ONESHOT_TIMERS_WITH_TIMEOUT_ZERO_EXITCODE:STRING=${EMBERBSD_EPOLL_ZERO_TIMER_EXITCODE}
.endif
.endif

.if !defined(OPSYS_HAS_KQUEUE)
PKG_SKIP_REASON+=	"Requires a kqueue implementation"
.endif

PLIST_VARS+=	eventfd timerfd
.if !defined(OPSYS_HAS_EVENTFD)
PLIST.eventfd=	YES
.endif
.if !defined(OPSYS_HAS_TIMERFD)
PLIST.timerfd=	YES
.endif

PKGCONFIG_OVERRIDE+=	epoll-shim-interpose.pc.cmakein
PKGCONFIG_OVERRIDE+=	epoll-shim.pc.cmakein

.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"

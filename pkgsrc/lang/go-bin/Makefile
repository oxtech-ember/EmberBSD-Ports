# $NetBSD: Makefile,v 1.25 2025/12/23 19:19:36 bsiegert Exp $

# EmberBSD: the official binary release of the one selected Go version,
# installed only as the explicit seed for building lang/go127 from source.
.include "../../lang/go/version.mk"
PKGNAME=	go-bin-${GO127_VERSION}
CATEGORIES=	lang
MASTER_SITES=	https://dl.google.com/go/

MAINTAINER=	tnn@NetBSD.org
HOMEPAGE=	https://golang.org/
COMMENT=	Bootstrap toolchain for lang/go*
LICENSE=	modified-bsd

NO_BUILD=	yes
PLIST_SRC=	${WRKDIR}/PLIST_DYNAMIC
USE_LANGUAGES=	# none
USE_TOOLS+=	pax perl:run bash:run
WRKSRC=		${WRKDIR}/go

.include "../../lang/go/go-vars.mk"

REPLACE_PERL+=			src/*/*.pl src/*/*/*.pl
REPLACE_PERL+=			src/net/http/cgi/testdata/test.cgi
REPLACE_BASH+=			*/*.bash */*/*.bash */*/*/*.bash */*/*/*/*.bash
REPLACE_BASH+=			*/*/*/*/*/*/*.bash */*/*/*/*/*/*/*.bash
REPLACE_BASH+=			*/*/*.sh */*/*/*.sh */*/*/*/*.sh */*/*/*/*/*/*/*.sh
REPLACE_BASH+=			lib/wasm/go_js_wasm_exec
REPLACE_BASH+=			lib/wasm/go_wasip1_wasm_exec
CHECK_INTERPRETER_SKIP+=	*/*.rc
CHECK_PORTABILITY_SKIP+=	misc/ios/clangwrap.sh
CHECK_SHLIBS_SUPPORTED=		no
CHECK_RELRO_SUPPORTED=		no

.include "../../mk/bsd.prefs.mk"

# One archive per supported build host platform; distinfo records each.
ONLY_FOR_PLATFORM+=		Darwin-*-aarch64
DIST.darwin-arm64=		go${PKGVERSION_NOREV}.darwin-arm64.tar.gz
.if ${MACHINE_PLATFORM:MDarwin-*-aarch64} || make(distinfo) || make(mdi)
DISTFILES+=			${DIST.darwin-arm64}
EXTRACT_ONLY+=			${DIST.darwin-arm64}
.endif

ONLY_FOR_PLATFORM+=		Darwin-*-x86_64
DIST.darwin-amd64=		go${PKGVERSION_NOREV}.darwin-amd64.tar.gz
.if ${MACHINE_PLATFORM:MDarwin-*-x86_64} || make(distinfo) || make(mdi)
DISTFILES+=			${DIST.darwin-amd64}
EXTRACT_ONLY+=			${DIST.darwin-amd64}
.endif

ONLY_FOR_PLATFORM+=		FreeBSD-*-aarch64
DIST.freebsd-arm64=		go${PKGVERSION_NOREV}.freebsd-arm64.tar.gz
.if ${MACHINE_PLATFORM:MFreeBSD-*-aarch64} || make(distinfo) || make(mdi)
DISTFILES+=			${DIST.freebsd-arm64}
EXTRACT_ONLY+=			${DIST.freebsd-arm64}
.endif

ONLY_FOR_PLATFORM+=		FreeBSD-*-x86_64
DIST.freebsd-amd64=		go${PKGVERSION_NOREV}.freebsd-amd64.tar.gz
.if ${MACHINE_PLATFORM:MFreeBSD-*-x86_64} || make(distinfo) || make(mdi)
DISTFILES+=			${DIST.freebsd-amd64}
EXTRACT_ONLY+=			${DIST.freebsd-amd64}
.endif

ONLY_FOR_PLATFORM+=		Linux-*-aarch64
DIST.linux-arm64=		go${PKGVERSION_NOREV}.linux-arm64.tar.gz
.if ${MACHINE_PLATFORM:MLinux-*-aarch64} || make(distinfo) || make(mdi)
DISTFILES+=			${DIST.linux-arm64}
EXTRACT_ONLY+=			${DIST.linux-arm64}
.endif

ONLY_FOR_PLATFORM+=		Linux-*-x86_64
DIST.linux-amd64=		go${PKGVERSION_NOREV}.linux-amd64.tar.gz
.if ${MACHINE_PLATFORM:MLinux-*-x86_64} || make(distinfo) || make(mdi)
DISTFILES+=			${DIST.linux-amd64}
EXTRACT_ONLY+=			${DIST.linux-amd64}
.endif

ONLY_FOR_PLATFORM+=		NetBSD-*-aarch64
DIST.netbsd-arm64=		go${PKGVERSION_NOREV}.netbsd-arm64.tar.gz
.if ${MACHINE_PLATFORM:MNetBSD-*-aarch64} || make(distinfo) || make(mdi)
DISTFILES+=			${DIST.netbsd-arm64}
EXTRACT_ONLY+=			${DIST.netbsd-arm64}
.endif

ONLY_FOR_PLATFORM+=		NetBSD-*-x86_64
DIST.netbsd-amd64=		go${PKGVERSION_NOREV}.netbsd-amd64.tar.gz
.if ${MACHINE_PLATFORM:MNetBSD-*-x86_64} || make(distinfo) || make(mdi)
DISTFILES+=			${DIST.netbsd-amd64}
EXTRACT_ONLY+=			${DIST.netbsd-amd64}
.endif

INSTALLATION_DIRS+=	go-bin

do-install:
	cd ${WRKSRC} && ${PAX} -rw . ${DESTDIR}${PREFIX}/go-bin

post-install:
	cd ${DESTDIR}${PREFIX} && find go-bin -type f -print	\
	    > ${WRKDIR}/PLIST_DYNAMIC

.include "../../mk/bsd.pkg.mk"

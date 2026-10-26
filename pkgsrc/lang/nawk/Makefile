# $NetBSD: Makefile,v 1.48 2025/07/26 05:37:46 rillig Exp $

DISTNAME=	nawk-20260426
PKGREVISION=	1
CATEGORIES=	lang
MASTER_SITES=	# empty
DISTFILES=	# empty

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/onetrueawk/awk/
COMMENT=	Brian Kernighan's pattern-directed scanning and processing language
LICENSE=	mit AND modified-bsd

POLICY_UPDATE_LIMITED=	bootstrap

BOOTSTRAP_PKG=	yes

.include "../../mk/bsd.prefs.mk"

.if defined(NAWK_COMMAND_SHELL)
.if empty(NAWK_COMMAND_SHELL:M/*) || !empty(NAWK_COMMAND_SHELL:tW:C,[[:space:]],?,g:C,[A-Za-z0-9_+./-],,g)
PKG_FAIL_REASON+= "NAWK_COMMAND_SHELL must be an absolute shell path with only letters, digits, _+./-"
.endif
CPPFLAGS+= -DNAWK_COMMAND_SHELL=\"${NAWK_COMMAND_SHELL}\"
.endif

CFLAGS+=	${CPPFLAGS} -DYYMAXDEPTH=300
MAKE_FLAGS+=	CC=${CC:Q} CFLAGS=${CFLAGS:M*:Q} LDFLAGS=${LDFLAGS:Q}

BUILD_TARGET=	a.out

INSTALLATION_DIRS=	bin ${PKGMANDIR}/man1

do-extract:
	${RUN}${CP} -R ${FILESDIR} ${WRKSRC}

do-install:
	${INSTALL_PROGRAM} ${WRKSRC}/a.out ${DESTDIR}${PREFIX}/bin/nawk
	${INSTALL_MAN} ${WRKSRC}/nawk.1 \
		${DESTDIR}${PREFIX}/${PKGMANDIR}/man1/nawk.1

.include "../../mk/bsd.pkg.mk"

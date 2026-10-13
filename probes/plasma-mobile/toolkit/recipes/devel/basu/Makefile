# $NetBSD: Makefile,v 1.1 2026/04/14 10:58:09 kikadf Exp $

DISTNAME=	basu-0.2.1
PKGREVISION=	2
CATEGORIES=	devel
MASTER_SITES=	https://git.sr.ht/~emersion/basu/archive/
EXTRACT_SUFX=	.tar.gz
SITES.${DISTNAME}${EXTRACT_SUFX}= -https://git.sr.ht/~emersion/basu/archive/v${PKGVERSION_NOREV}${EXTRACT_SUFX}

MAINTAINER=	kikadf.01@gmail.com
HOMEPAGE=	https://sr.ht/~emersion/basu/
COMMENT=	The sd-bus library, extracted from systemd
LICENSE=	gnu-lgpl-v2.1

USE_TOOLS+=	pkg-config
TOOL_DEPENDS+=	gperf>=3.3:../../devel/gperf
WRKSRC=		${WRKDIR}/basu-v${PKGVERSION_NOREV}
# Origin: EmberBSD (AI-assisted). This generator runs on the build host.
PYTHON_FOR_BUILD_ONLY=	tool
REPLACE_TOOL_PYTHON=	src/basic/generate-gperfs.py
# Do not select an older platform gperf before the declared native tool.
MESON_BINARIES+=	gperf
MESON_BINARY.gperf=	${TOOLBASE}/bin/gperf
MESON_ARGS+=	-Daudit=disabled
MESON_ARGS+=	-Dlibcap=disabled

.include "../../devel/meson/build.mk"
.include "../../lang/python/application.mk"
.include "../../mk/bsd.pkg.mk"

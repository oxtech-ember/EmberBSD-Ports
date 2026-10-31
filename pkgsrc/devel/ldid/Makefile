# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).

DISTNAME=	ldid-2.1.5-procursus7
PKGNAME=	ldid-2.1.5.7
CATEGORIES=	devel
MASTER_SITES=	${MASTER_SITE_GITHUB:=ProcursusTeam/}
GITHUB_PROJECT=	ldid
GITHUB_TAG=	v2.1.5-procursus7

HOMEPAGE=	https://github.com/ProcursusTeam/ldid
COMMENT=	Mach-O ad-hoc signing and entitlement tool
LICENSE=	gnu-agpl-v3

USE_LANGUAGES=	c c++11
USE_TOOLS+=	gmake pkg-config
MAKE_FLAGS+=	VERSION=2.1.5-procursus7

.include "../../security/openssl/buildlink3.mk"
.include "../../textproc/libplist/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

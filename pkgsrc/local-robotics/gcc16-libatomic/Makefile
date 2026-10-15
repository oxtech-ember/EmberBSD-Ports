# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), standalone component of the common GCC16 runtime.
DISTNAME=	gcc-16.2.0
PKGNAME=	gcc16-libatomic-16.2.0
CATEGORIES=	lang
MASTER_SITES=	https://gcc.gnu.org/pub/gcc/releases/gcc-16.2.0/
EXTRACT_SUFX=	.tar.xz

HOMEPAGE=	https://gcc.gnu.org/
COMMENT=	GCC16 atomic runtime for an incomplete cross SDK
# COPYING.RUNTIME grants the GCC Runtime Library Exception 3.1.
LICENSE=	gnu-gpl-v3

# Full GCC packages already own these files. This component extends only a
# partial SDK; it must never replace an installed complete runtime provider.
CONFLICTS+=	gcc16-[0-9]* gcc16-libs-[0-9]*
USE_LANGUAGES=	c
GCC_REQD+=	16.2
USE_TOOLS+=	gmake
GNU_CONFIGURE=	yes
GNU_CONFIGURE_PREFIX=	${PREFIX}/gcc16
CONFIGURE_DIRS=	libatomic
CONFIGURE_ARGS+=	--enable-shared --enable-static --disable-multilib
BUILD_TARGET=	libatomic.la
INSTALL_TARGET=	install-toolexeclibLTLIBRARIES

post-install:
	${INSTALL_DATA_DIR} ${DESTDIR}${PREFIX}/share/licenses/gcc16-libatomic
	${INSTALL_DATA} ${WRKSRC}/COPYING3 ${WRKSRC}/COPYING.RUNTIME \
	    ${FILESDIR}/SOURCE ${DESTDIR}${PREFIX}/share/licenses/gcc16-libatomic

.include "../../mk/pthread.buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

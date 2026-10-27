# $NetBSD$
# Origin: Retro68, Wolfgang Thaller and contributors.

DISTNAME= Retro68-0.0.20261022
PKGNAME= retro68-rez-0.0.20261022
CATEGORIES= devel
MASTER_SITES= ${MASTER_SITE_GITHUB:=autc04/}
GITHUB_PROJECT= Retro68
GITHUB_TAG= 0cbd3cb918a127a0d30a675b337f8f8e15062786
WRKSRC= ${WRKDIR}/Retro68-${GITHUB_TAG}

MAINTAINER= pkgsrc-users@NetBSD.org
HOMEPAGE= https://github.com/autc04/Retro68/
COMMENT= Classic Macintosh resource compiler and resource file utilities
LICENSE= gnu-gpl-v3

PATCH_STRIP= -p1
USE_LANGUAGES= c c++17
USE_TOOLS+= bison
CMAKE_CONFIGURE_ARGS+= -DRETRO68_REZ_ONLY=ON
CMAKE_CONFIGURE_ARGS+= -DHFS_INCLUDE_DIR=${BUILDLINK_DIR}/include/libhfs
CMAKE_CONFIGURE_ARGS+= -DHFS_LIBRARY=${BUILDLINK_DIR}/lib/libhfs.${SHLIB_EXT}
INSTALLATION_DIRS+= share/licenses/retro68-rez

post-install:
	${INSTALL_DATA} ${WRKSRC}/COPYING ${DESTDIR}${PREFIX}/share/licenses/retro68-rez/COPYING

.include "../../devel/cmake/build.mk"
.include "../../devel/boost-libs/buildlink3.mk"
.include "../../devel/libhfs/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

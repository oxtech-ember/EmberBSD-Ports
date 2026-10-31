# Common xdiff source from the same distribution and patch set as Git.
.include "../../devel/git/Makefile.common"

PKGNAME= git-xdiff-source-${GIT_VERSION}
PKGREVISION= 2
COMMENT= Patched Git xdiff sources for other source-level consumers
LICENSE= gnu-lgpl-v2.1 AND mit

USE_LANGUAGES= # none
NO_CONFIGURE= yes
NO_BUILD= yes
INSTALLATION_DIRS= share/git-xdiff-source/xdiff

XDIFF_FILES= xdiff.h xdiffi.c xdiffi.h xemit.c xemit.h xhistogram.c \
 xinclude.h xmacros.h xmerge.c xpatience.c xprepare.c xprepare.h \
 xtypes.h xutils.c xutils.h

do-install:
.for file in ${XDIFF_FILES}
	${INSTALL_DATA} ${WRKSRC}/xdiff/${file} ${DESTDIR}${PREFIX}/share/git-xdiff-source/xdiff/${file}
.endfor
	${INSTALL_DATA} ${WRKSRC}/COPYING ${DESTDIR}${PREFIX}/share/git-xdiff-source/COPYING.git
	${INSTALL_DATA} ${PKGSRCDIR}/licenses/gnu-lgpl-v2.1 ${DESTDIR}${PREFIX}/share/git-xdiff-source/COPYING.LGPL-2.1

.include "../../mk/bsd.pkg.mk"

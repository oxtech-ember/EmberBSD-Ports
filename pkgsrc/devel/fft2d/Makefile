# Origin: Takuya Ooura FFT, TensorFlow FFT declarations (Apache-2.0).
DISTNAME= fft2d-20061228
PKGNAME= fft2d-source-20061228
CATEGORIES= devel
MASTER_SITES= -https://www.kurims.kyoto-u.ac.jp/~ooura/fft2d.tgz
EXTRACT_SUFX= .tgz
WRKSRC= ${WRKDIR}/fft2d
HOMEPAGE= https://www.kurims.kyoto-u.ac.jp/~ooura/fft.html
COMMENT= Shared Ooura FFT source and declarations
LICENSE= ooura-fft AND apache-2.0
NO_ARCH= yes
NO_BUILD= yes
NO_CONFIGURE= yes
USE_LANGUAGES= # source only
USE_TOOLS+= find sort tar

# pkgsrc patch may create backups for newly added declaration and notice files.
post-patch:
	${RM} -f ${WRKSRC:Q}/fft.h.orig ${WRKSRC:Q}/fft2d.h.orig \
	    ${WRKSRC:Q}/LICENSE.ooura.orig ${WRKSRC:Q}/LICENSE.apache-2.0.orig

do-install:
	${INSTALL_DATA_DIR} ${DESTDIR:Q}${PREFIX:Q}/share/fft2d-source
	${TAR} -cf ${WRKDIR:Q}/fft2d-source.tar -C ${WRKSRC:Q} .
	${TAR} -xf ${WRKDIR:Q}/fft2d-source.tar -C ${DESTDIR:Q}${PREFIX:Q}/share/fft2d-source

GENERATE_PLIST+= cd ${DESTDIR:Q}${PREFIX:Q}; ${FIND} share/fft2d-source \( -type f -o -type l \) -print | ${SORT};
.include "../../mk/bsd.pkg.mk"

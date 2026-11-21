# Origin: EmberBSD (AI-assisted); upstream gyp-next, BSD-3-Clause.
DISTNAME=	gyp-next-0.22.4
PKGNAME=	${PYPKGPREFIX}-gyp-0.22.4
PKGREVISION=	2
CATEGORIES=	devel
MASTER_SITES=	${MASTER_SITE_GITHUB:=nodejs/}
GITHUB_PROJECT=	gyp-next
GITHUB_TAG=	v${PKGVERSION_NOREV}
HOMEPAGE=	https://github.com/nodejs/gyp-next/
COMMENT=	Shared GYP source provider
LICENSE=	modified-bsd

NO_ARCH=	yes
NO_BUILD=	yes
USE_LANGUAGES=	# source provider
USE_TOOLS+=	find sort tar
PYTHON_FOR_BUILD_ONLY= tool
BUILD_DEFS+=	EMBERBSD_SDK_SOURCE
DEPENDS+=	${PYPKGPREFIX}-packaging>=26.3:../../devel/py-packaging

# Do not install the bundled packaging copy: use the common Python package.
do-install:
	${INSTALL_DATA_DIR} ${DESTDIR}${PREFIX}/share/gyp
	cd ${WRKSRC} && ${TAR} --exclude './pylib/packaging' --exclude '*.orig' --exclude '*.rej' -cf ${WRKDIR}/gyp-source.tar .
	cd ${DESTDIR}${PREFIX}/share/gyp && ${TAR} -xf ${WRKDIR}/gyp-source.tar
	${INSTALL_DATA_DIR} ${DESTDIR}${PREFIX}/bin ${DESTDIR}${PREFIX}/${PYSITELIB}
	${TOOL_PYTHONBIN:Q} -B -I -S ${FILESDIR:Q}/portable-scripts.py ${DESTDIR:Q}${PREFIX:Q}/share/gyp ${PYTHONBIN:T:Q} ${DESTDIR:Q}${PREFIX:Q}/${PYSITELIB:Q}/gyp
	${PRINTF} '%s\n' '#!/bin/sh' 'exec "${PYTHONBIN}" -B "${PREFIX}/share/gyp/gyp_main.py" "$$@"' > ${DESTDIR:Q}${PREFIX:Q}/bin/gyp
	${CHMOD} ${BINMODE} ${DESTDIR:Q}${PREFIX:Q}/bin/gyp
	${INSTALL_DATA_DIR} ${DESTDIR}${PREFIX}/${PYSITELIB}/gyp_next-0.22.4.dist-info
	${PRINTF} 'Metadata-Version: 2.3\nName: gyp-next\nVersion: 0.22.4\n' > ${DESTDIR}${PREFIX}/${PYSITELIB}/gyp_next-0.22.4.dist-info/METADATA
	${TOOL_PYTHONBIN:Q} -B -I -S ${FILESDIR:Q}/stamp-source.py --sdk-source ${EMBERBSD_SDK_SOURCE:Q} --source ${DESTDIR:Q}${PREFIX:Q}/share/gyp --pkgsrc-root ${_PKGSRCDIR:Q}

GENERATE_PLIST+= ${ECHO} bin/gyp; ${ECHO} ${PYSITELIB}/gyp_next-0.22.4.dist-info/METADATA;
GENERATE_PLIST+= cd ${DESTDIR}${PREFIX}; ${FIND} ${PYSITELIB}/gyp share/gyp \( -type f -o -type l \) -print | ${SORT};
.include "../../lang/python/application.mk"
.include "../../lang/python/tool.mk"
.include "../../mk/bsd.pkg.mk"

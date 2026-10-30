# Origin: EmberBSD (AI-assisted); upstream gyp-next, BSD-3-Clause.
DISTNAME=	gyp-next-0.22.4
PKGNAME=	${PYPKGPREFIX}-gyp-0.22.4
CATEGORIES=	devel
MASTER_SITES=	${MASTER_SITE_GITHUB:=nodejs/}
GITHUB_PROJECT=	gyp-next
GITHUB_TAG=	v${PKGVERSION_NOREV}
HOMEPAGE=	https://github.com/nodejs/gyp-next/
COMMENT=	Shared GYP source provider
LICENSE=	modified-bsd

NO_ARCH=	yes
NO_BUILD=	yes
NO_CONFIGURE=	yes
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
	${SED} -e '1s,.*,#!${PYTHONBIN},' ${WRKSRC}/gyp_main.py > ${WRKDIR}/gyp_main.py
	${INSTALL_SCRIPT} ${WRKDIR}/gyp_main.py ${DESTDIR}${PREFIX}/share/gyp/gyp_main.py
	${INSTALL_DATA_DIR} ${DESTDIR}${PREFIX}/bin ${DESTDIR}${PREFIX}/${PYSITELIB}
	${LN} -s ../share/gyp/gyp_main.py ${DESTDIR}${PREFIX}/bin/gyp
	${LN} -s ../../../share/gyp/pylib/gyp ${DESTDIR}${PREFIX}/${PYSITELIB}/gyp
	${INSTALL_DATA_DIR} ${DESTDIR}${PREFIX}/${PYSITELIB}/gyp_next-0.22.4.dist-info
	${PRINTF} 'Metadata-Version: 2.3\nName: gyp-next\nVersion: 0.22.4\n' > ${DESTDIR}${PREFIX}/${PYSITELIB}/gyp_next-0.22.4.dist-info/METADATA
	${TOOL_PYTHONBIN:Q} -B -I -S ${FILESDIR:Q}/stamp-source.py --sdk-source ${EMBERBSD_SDK_SOURCE:Q} --source ${DESTDIR:Q}${PREFIX:Q}/share/gyp --pkgsrc-root ${_PKGSRCDIR:Q}

GENERATE_PLIST+= ${ECHO} bin/gyp; ${ECHO} ${PYSITELIB}/gyp; ${ECHO} ${PYSITELIB}/gyp_next-0.22.4.dist-info/METADATA;
GENERATE_PLIST+= cd ${DESTDIR}${PREFIX}; ${FIND} share/gyp \( -type f -o -type l \) -print | ${SORT};
.include "../../lang/python/application.mk"
.include "../../lang/python/tool.mk"
.include "../../mk/bsd.pkg.mk"

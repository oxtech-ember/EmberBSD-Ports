# Python bindings from the shared dtc source and patch set.
.include "../../sysutils/dtc/Makefile.common"

DISTNAME=		dtc-${DTC_VERSION}
PKGNAME=		${PYPKGPREFIX}-pylibfdt-${DTC_VERSION}
CATEGORIES=		sysutils python
MASTER_SITES=		https://www.kernel.org/pub/software/utils/dtc/
EXTRACT_SUFX=		.tar.xz
DISTINFO_FILE=		${.CURDIR}/../../sysutils/dtc/distinfo
PATCHDIR=		${.CURDIR}/../../sysutils/dtc/patches

MAINTAINER=		pkgsrc-users@NetBSD.org
HOMEPAGE=		https://www.devicetree.org/
COMMENT=		Python bindings for the Device Tree Compiler library
LICENSE=		gnu-gpl-v2

PY_PATCHPLIST=		yes
USE_LANGUAGES=		c
USE_LIBTOOL=		yes

TOOL_DEPENDS+=		swig4>=4.5.1:../../devel/swig4
TOOLS_CREATE+=		swig
TOOLS_PATH.swig=	${TOOLBASE}/bin/swig4.0

INSTALLATION_DIRS+=	${PYSITELIB}

do-build:
	cd ${WRKSRC}/pylibfdt && ${TOOLS_PATH.swig} -python \
	    -I${WRKSRC}/libfdt -o libfdt.c libfdt.i
	cd ${WRKSRC}/pylibfdt && ${LIBTOOL} --tag=CC --mode=compile \
	    ${CC} ${CPPFLAGS} ${CFLAGS} -I${BUILDLINK_DIR}/${PYINC} \
	    -DPY_SSIZE_T_CLEAN -c libfdt.c -o libfdt.lo
	cd ${WRKSRC}/pylibfdt && ${LIBTOOL} --tag=CC --mode=link \
	    ${CC} ${CFLAGS} ${LDFLAGS} -module -avoid-version \
	    -rpath ${PREFIX}/${PYSITELIB} -o _libfdt.la libfdt.lo -lfdt

do-install:
	${INSTALL_LIB} ${WRKSRC}/pylibfdt/.libs/_libfdt.so \
	    ${DESTDIR}${PREFIX}/${PYSITELIB}/_libfdt.so
	${INSTALL_DATA} ${WRKSRC}/pylibfdt/libfdt.py \
	    ${DESTDIR}${PREFIX}/${PYSITELIB}/libfdt.py
	${TOOL_PYTHONBIN} -m compileall -q -d ${PREFIX}/${PYSITELIB} \
	    ${DESTDIR}${PREFIX}/${PYSITELIB}/libfdt.py

BUILDLINK_API_DEPENDS.dtc+=	dtc>=${DTC_VERSION}
BUILDLINK_ABI_DEPENDS.dtc+=	dtc>=${DTC_VERSION}

.include "../../sysutils/dtc/buildlink3.mk"
.include "../../lang/python/tool.mk"
.include "../../lang/python${PYTHON_VERSION}/buildlink3.mk"
.include "../../lang/python/extension.mk"

.if ${USE_CROSS_COMPILE:tl} != "yes"
do-test:
	${SETENV} PYTHONPATH=${WRKSRC}/pylibfdt:${WRKSRC}/pylibfdt/.libs \
	    ${TOOL_PYTHONBIN} ${FILESDIR}/test-pylibfdt.py
.endif

.include "../../mk/bsd.pkg.mk"

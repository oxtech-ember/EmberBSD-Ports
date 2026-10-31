# $NetBSD: Makefile,v 1.158 2026/09/08 05:08:26 adam Exp $
# Origin: pkgsrc math/py-numpy; EmberBSD (AI-assisted) adds the blas option.

DISTNAME=	numpy-2.5.3
PKGNAME=	${PYPKGPREFIX}-${DISTNAME}
PKGREVISION=	1
CATEGORIES=	math python
MASTER_SITES=	${MASTER_SITE_PYPI:=n/numpy/}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://numpy.org/
COMMENT=	Array processing for numbers, strings, records, and objects
LICENSE=	modified-bsd

TOOL_DEPENDS+=	${PYPKGPREFIX}-meson_python>=0:../../devel/py-meson_python
TOOL_DEPENDS+=	${PYPKGPREFIX}-cython>=0:../../devel/py-cython
TEST_DEPENDS+=	${PYPKGPREFIX}-hypothesis>=0:../../devel/py-hypothesis
TEST_DEPENDS+=	${PYPKGPREFIX}-test>=0:../../devel/py-test
TEST_DEPENDS+=	${PYPKGPREFIX}-typing-extensions>=4.2.0:../../devel/py-typing-extensions

USE_CC_FEATURES=	c11
USE_CXX_FEATURES=	c++17
USE_LANGUAGES=		c c++
USE_TOOLS+=		pkg-config
# meson checks for gcc 10.3
GCC_REQD+=		10

PYTHON_VERSIONS_INCOMPATIBLE=	310 311

.include "../../math/py-numpy/make_env.mk"

REPLACE_PYTHON+=	*.py */*.py */*/*.py */*/*/*.py */*/*/*/*.py

.include "../../lang/python/pyversion.mk"
.include "options.mk"

# XXX Avoid picking up other compilers when installed
.include "../../mk/compiler.mk"

.if defined(PKGSRC_FORTRAN) && ${PKGSRC_FORTRAN} == "g95"
PYSETUPBUILDARGS+=	--fcompiler=g95
.elif defined(PKGSRC_FORTRAN) && ${PKGSRC_FORTRAN} == "gfortran"
PYSETUPBUILDARGS+=	--fcompiler=gnu95
.elif !empty(PKGSRC_COMPILER:Mgcc)
PYSETUPBUILDARGS+=	--fcompiler=gnu
.endif

# This package bypasses the wrappers and calls the compilers directly when
# linking, so ensure that we pass through requisite options.
LDFLAGS+=		${_COMPILER_ABI_FLAG.${ABI}}

# Check if the numpy/scipy ecosystem is ready for full ILP64 before
# allowing/setting BLAS_INDEX64=yes. Scipy needs both variants right now,
# wich does not work without standardized symbol suffix.
# Will need -Csetup-args=Duse-ilp64, too.
# TODO: accelerate.framework has no pkg-config yet (see blas.buildlink3.mk).
.if !empty(PKG_OPTIONS:Mblas)
BLAS_ACCEPTED=		${_BLAS_TYPES}
BLAS_C_INTERFACE=	yes
# Cblas and lapack API (not lapacke) is desired.
# Meson build uses pkg-config since 1.26.2 (or elaborate own logic not
# suitable here) and guesses for cblas if blas lib does not contain the
# C interface. That covers netlib for us, and openblas builds serve
# all APIs.
WHEEL_ARGS+=		-Csetup-args=-Dblas=${BLAS_PC}
WHEEL_ARGS+=		-Csetup-args=-Dlapack=${LAPACK_PC}
.else
# Without the option, numpy uses its own lapack_lite routines. They are
# slower, but they need no BLAS package and no Fortran compiler.
WHEEL_ARGS+=		-Csetup-args=-Dblas=none
WHEEL_ARGS+=		-Csetup-args=-Dlapack=none
WHEEL_ARGS+=		-Csetup-args=-Dallow-noblas=true
.endif
WHEEL_ARGS+=		-Ccompile-args=-j${MAKE_JOBS:U1}

# disable AVX 512 on old NetBSD; support on NetBSD < 11 was incomplete, see PR 58539
.if ${OPSYS} == "NetBSD" && ${OPSYS_VERSION} < 110000
WHEEL_ARGS+=		-Csetup-args=-Dcpu-dispatch="max -avx512f -avx512cd -avx512_knl -avx512_knm -avx512_skx -avx512_clx -avx512_cnl -avx512_icl -avx512_spr"
.endif

# Remove invalid __STDC_VERSION__ setting
BUILDLINK_TRANSFORM.SunOS+=	rm:-D__STDC_VERSION__=0

# Cython is a tool dependency and runs on the build machine.
pre-configure:
	${LN} -sf ${TOOLBASE}/bin/cython-${PYVERSSUFFIX} ${BUILDLINK_DIR}/bin/cython

PY_RENAME_BINARIES=	f2py numpy-config

SUBST_CLASSES+=		paths
SUBST_STAGE.paths=	pre-configure
SUBST_MESSAGE.paths=	Fixing path to numpy-configure (for tests).
SUBST_FILES.paths=	numpy/tests/test_configtool.py
SUBST_SED.paths=	-e 's,'numpy-config','numpy-config-${PYVERSSUFFIX}',g'

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# Meson runs these build scripts by their #! line on the build machine,
# where the target interpreter from REPLACE_PYTHON does not exist.
SUBST_CLASSES+=		buildpy
SUBST_STAGE.buildpy=	post-configure
SUBST_MESSAGE.buildpy=	Running the build scripts with the build machine Python.
SUBST_FILES.buildpy=	numpy/_build_utils/*.py
SUBST_FILES.buildpy+=	numpy/_core/code_generators/verify_c_api_version.py
SUBST_SED.buildpy=	-e '1s,^\#!${PYTHONBIN},\#!${TOOL_PYTHONBIN},'
SUBST_NOOP_OK.buildpy=	yes
# numpy/_core/meson.build runs a target program to learn the long double
# format unless the cross file names it. The values are those of the
# psABIs: IEEE binary128 on AArch64 and RISC-V, x87 extended on x86_64.
MESON_CROSS_ARCH_VARS+=			longdouble_format
MESON_CROSS.aarch64.longdouble_format=	'IEEE_QUAD_LE'
MESON_CROSS.riscv64.longdouble_format=	'IEEE_QUAD_LE'
MESON_CROSS.x86_64.longdouble_format=	'INTEL_EXTENDED_16_BYTES_LE'
.endif

# as of 2.5.1
# 35 failed, 47794 passed, 336 skipped, 3634 deselected, 33 xfailed, 1 xpassed, 14 warnings
do-test:
	cd ${WRKDIR} && \
	${SETENV} ${TEST_ENV} PYTHONPATH=${DESTDIR}${PREFIX}/${PYSITELIB} ${PYTHONBIN} -c "import numpy; numpy.test()"

.include "../../lang/python/application.mk"
.include "../../lang/python/wheel.mk"
.if !empty(PKG_OPTIONS:Mblas)
.include "../../mk/blas.buildlink3.mk"
.endif
.include "../../mk/bsd.pkg.mk"

# $NetBSD: buildlink3.mk,v 1.22 2026/02/17 12:06:50 wiz Exp $
# Origin: pkgsrc math/py-numpy; EmberBSD (AI-assisted) follows the blas option.

BUILDLINK_TREE+=	py-numpy

.if !defined(PY_NUMPY_BUILDLINK3_MK)
PY_NUMPY_BUILDLINK3_MK:=

USE_CXX_FEATURES+=	c++17

.include "../../lang/python/pyversion.mk"

BUILDLINK_API_DEPENDS.py-numpy+=	${PYPKGPREFIX}-numpy>=1.0
BUILDLINK_ABI_DEPENDS.py-numpy+=	${PYPKGPREFIX}-numpy>=1.20.3nb1
BUILDLINK_PKGSRCDIR.py-numpy?=		../../math/py-numpy

BUILDLINK_TARGETS+=	buildlink-numpy-unversioned
.PHONY: buildlink-numpy-unversioned
buildlink-numpy-unversioned:
	${LN} -s ${PREFIX}/${PYSITELIB}/numpy/_core/lib/pkgconfig/numpy.pc \
		${BUILDLINK_DIR}/lib/pkgconfig/numpy.pc

.include "../../mk/bsd.fast.prefs.mk"

# Ask the installed package by its real name, for example py315-numpy.
pkgbase := ${PYPKGPREFIX}-numpy
BUILDLINK_PKGSRCDIR.${PYPKGPREFIX}-numpy?=	${BUILDLINK_PKGSRCDIR.py-numpy}
.include "../../mk/pkg-build-options.mk"

# Without the blas option, numpy has no BLAS to pass on to its users.
.if ${PKG_BUILD_OPTIONS.${PYPKGPREFIX}-numpy:Mblas}
.include "../../math/py-numpy/make_env.mk"

BLAS_C_INTERFACE=	yes
.include "../../mk/blas.buildlink3.mk"
.endif

.endif # PY_NUMPY_BUILDLINK3_MK

BUILDLINK_TREE+=	-py-numpy

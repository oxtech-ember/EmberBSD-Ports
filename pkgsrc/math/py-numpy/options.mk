# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
# blas: link a BLAS and LAPACK package. These packages need a Fortran
# compiler. Without the option, numpy uses its internal lapack_lite code,
# so a compiler set without Fortran can build numpy.

PKG_OPTIONS_VAR=	PKG_OPTIONS.py-numpy
PKG_SUPPORTED_OPTIONS=	blas
PKG_SUGGESTED_OPTIONS=	blas

.include "../../mk/bsd.options.mk"

.if !empty(PKG_OPTIONS:Mblas)
USE_LANGUAGES+=		fortran
.endif

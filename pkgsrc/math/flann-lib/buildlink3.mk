# SPDX-License-Identifier: BSD-2-Clause
BUILDLINK_TREE+=	flann-lib

.if !defined(FLANN_LIB_BUILDLINK3_MK)
FLANN_LIB_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.flann-lib+=	flann-lib>=1.9.2
BUILDLINK_ABI_DEPENDS.flann-lib+=	flann-lib-1.9.2{,nb*}
BUILDLINK_PKGSRCDIR.flann-lib?=	../../math/flann-lib
USE_CXX_FEATURES+=	c++17
.include "../../archivers/lz4/buildlink3.mk"
.endif

BUILDLINK_TREE+=	-flann-lib

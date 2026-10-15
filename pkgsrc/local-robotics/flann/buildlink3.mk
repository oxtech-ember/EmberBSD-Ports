# SPDX-License-Identifier: BSD-2-Clause
BUILDLINK_TREE+=	flann

.if !defined(FLANN_BUILDLINK3_MK)
FLANN_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.flann+=	flann>=1.9.2
BUILDLINK_ABI_DEPENDS.flann+=	flann-1.9.2{,nb*}
BUILDLINK_PKGSRCDIR.flann?=	../../local-robotics/flann
USE_CXX_FEATURES+=	c++17
GCC_REQD+=	16.2
.include "../../local-robotics/lz4/buildlink3.mk"
.endif

BUILDLINK_TREE+=	-flann

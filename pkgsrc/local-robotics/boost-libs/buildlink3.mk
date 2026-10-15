# SPDX-License-Identifier: BSD-2-Clause
BUILDLINK_TREE+=	boost-libs

.if !defined(BOOST_LIBS_BUILDLINK3_MK)
BOOST_LIBS_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.boost-libs+=	boost-libs>=1.92.0
BUILDLINK_ABI_DEPENDS.boost-libs+=	boost-libs-1.92.0{,nb*}
BUILDLINK_PKGSRCDIR.boost-libs?=	../../local-robotics/boost-libs
USE_CXX_FEATURES+=	c++17
GCC_REQD+=		16.2
.include "../../local-robotics/boost-headers/buildlink3.mk"
.endif

BUILDLINK_TREE+=	-boost-libs

# SPDX-License-Identifier: BSD-2-Clause
BUILDLINK_TREE+=	ompl
.if !defined(OMPL_BUILDLINK3_MK)
OMPL_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.ompl+=	ompl>=2.0.2
BUILDLINK_ABI_DEPENDS.ompl+=	ompl-2.0.2{,nb*}
BUILDLINK_PKGSRCDIR.ompl?=	../../local-robotics/ompl
USE_CXX_FEATURES+=	c++17
GCC_REQD+=		16.2
.include "../../local-robotics/eigen3/buildlink3.mk"
.include "../../local-robotics/boost-libs/buildlink3.mk"
.endif
BUILDLINK_TREE+=	-ompl

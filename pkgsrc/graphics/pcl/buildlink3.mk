# SPDX-License-Identifier: MIT
BUILDLINK_TREE+=	pcl
.if !defined(PCL_BUILDLINK3_MK)
PCL_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.pcl+=	pcl>=1.15.1nb1
BUILDLINK_ABI_DEPENDS.pcl+=	pcl-1.15.1nb*
BUILDLINK_PKGSRCDIR.pcl?=	../../graphics/pcl
USE_CXX_FEATURES+=	c++17
.include "../../math/eigen3/buildlink3.mk"
.include "../../devel/boost-libs/buildlink3.mk"
.include "../../math/flann-lib/buildlink3.mk"
.endif
BUILDLINK_TREE+=	-pcl

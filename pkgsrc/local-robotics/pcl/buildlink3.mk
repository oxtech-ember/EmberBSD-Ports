# SPDX-License-Identifier: MIT
BUILDLINK_TREE+=	pcl
.if !defined(PCL_BUILDLINK3_MK)
PCL_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.pcl+=	pcl>=1.15.1
BUILDLINK_ABI_DEPENDS.pcl+=	pcl-1.15.1{,nb*}
BUILDLINK_PKGSRCDIR.pcl?=	../../local-robotics/pcl
USE_CXX_FEATURES+=	c++17
GCC_REQD+=		16.2
.include "../../local-robotics/eigen3/buildlink3.mk"
.include "../../local-robotics/boost-iostreams/buildlink3.mk"
.include "../../local-robotics/boost-libs/buildlink3.mk"
.include "../../local-robotics/flann/buildlink3.mk"
.endif
BUILDLINK_TREE+=	-pcl

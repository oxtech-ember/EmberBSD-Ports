# SPDX-License-Identifier: MIT
BUILDLINK_TREE+=	gtsam
.if !defined(GTSAM_BUILDLINK3_MK)
GTSAM_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.gtsam+=	gtsam>=4.3.0
BUILDLINK_ABI_DEPENDS.gtsam+=	gtsam-4.3.0{,nb*}
BUILDLINK_PKGSRCDIR.gtsam?=	../../local-robotics/gtsam
USE_CXX_FEATURES+=	c++17
GCC_REQD+=		16.2
.include "../../local-robotics/eigen3/buildlink3.mk"
.endif
BUILDLINK_TREE+=	-gtsam

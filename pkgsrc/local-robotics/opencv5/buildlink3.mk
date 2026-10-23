# SPDX-License-Identifier: MIT
BUILDLINK_TREE+= opencv5
.if !defined(OPENCV5_BUILDLINK3_MK)
OPENCV5_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.opencv5+= opencv5>=5.0.0
BUILDLINK_ABI_DEPENDS.opencv5+= opencv5>=5.0.0
BUILDLINK_PKGSRCDIR.opencv5?= ../../local-robotics/opencv5
.include "../../math/eigen3/buildlink3.mk"
.include "../../graphics/libjpeg-turbo/buildlink3.mk"
.include "../../graphics/png/buildlink3.mk"
.endif
BUILDLINK_TREE+= -opencv5

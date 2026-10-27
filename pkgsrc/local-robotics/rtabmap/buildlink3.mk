# SPDX-License-Identifier: MIT
BUILDLINK_TREE+= rtabmap
.if !defined(RTABMAP_BUILDLINK3_MK)
RTABMAP_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.rtabmap+= rtabmap>=0.23.8
BUILDLINK_ABI_DEPENDS.rtabmap+= rtabmap>=0.23.8
BUILDLINK_PKGSRCDIR.rtabmap?= ../../local-robotics/rtabmap
.include "../../local-robotics/opencv5/buildlink3.mk"
.include "../../graphics/pcl/buildlink3.mk"
.include "../../local-robotics/gtsam/buildlink3.mk"
.include "../../databases/sqlite3/buildlink3.mk"
.endif
BUILDLINK_TREE+= -rtabmap

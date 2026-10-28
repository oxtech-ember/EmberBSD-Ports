# $NetBSD: buildlink3.mk,v 1.36 2026/08/26 10:19:07 adam Exp $

BUILDLINK_TREE+=	opencv-contrib

.if !defined(OPENCV_CONTRIB_BUILDLINK3_MK)
OPENCV_CONTRIB_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.opencv-contrib+=	opencv-contrib>=5.0.0
BUILDLINK_ABI_DEPENDS.opencv-contrib?=	opencv-contrib>=5.0.0
BUILDLINK_PKGSRCDIR.opencv-contrib?=	../../graphics/opencv-contrib

.include "../../graphics/opencv/buildlink3.mk"
.endif	# OPENCV_CONTRIB_BUILDLINK3_MK

BUILDLINK_TREE+=	-opencv-contrib

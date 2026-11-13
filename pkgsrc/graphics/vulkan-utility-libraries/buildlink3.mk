# $NetBSD$

BUILDLINK_TREE+=	vulkan-utility-libraries

.if !defined(VULKAN_UTILITY_LIBRARIES_BUILDLINK3_MK)
VULKAN_UTILITY_LIBRARIES_BUILDLINK3_MK:=

BUILDLINK_DEPMETHOD.vulkan-utility-libraries?=	build
BUILDLINK_API_DEPENDS.vulkan-utility-libraries+=	vulkan-utility-libraries>=1.4.363.0
BUILDLINK_PKGSRCDIR.vulkan-utility-libraries?=	../../graphics/vulkan-utility-libraries

.include "../../graphics/vulkan-headers/buildlink3.mk"
.endif

BUILDLINK_TREE+=	-vulkan-utility-libraries

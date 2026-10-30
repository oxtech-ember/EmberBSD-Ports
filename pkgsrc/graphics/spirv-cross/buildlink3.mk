# $NetBSD$
BUILDLINK_TREE+= spirv-cross
.if !defined(SPIRV_CROSS_BUILDLINK3_MK)
SPIRV_CROSS_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.spirv-cross+= spirv-cross>=1.4.363.0
# The descriptor-heap fix changes internal C++ metadata and header definitions.
BUILDLINK_ABI_DEPENDS.spirv-cross+= spirv-cross>=1.4.363.0nb2
BUILDLINK_PKGSRCDIR.spirv-cross?= ../../graphics/spirv-cross
# Preserve all upstream CMake package exports for installed consumers.
BUILDLINK_FILES.spirv-cross+= share/spirv_cross_*/cmake/*
.endif
BUILDLINK_TREE+= -spirv-cross

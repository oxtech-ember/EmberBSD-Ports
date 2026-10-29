# $NetBSD$
BUILDLINK_TREE+= spirv-cross
.if !defined(SPIRV_CROSS_BUILDLINK3_MK)
SPIRV_CROSS_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.spirv-cross+= spirv-cross>=1.4.363.0
BUILDLINK_ABI_DEPENDS.spirv-cross+= spirv-cross>=1.4.363.0
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && \
    ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
BUILDLINK_ABI_DEPENDS.spirv-cross+= spirv-cross>=1.4.363.0nb1
.endif
BUILDLINK_PKGSRCDIR.spirv-cross?= ../../graphics/spirv-cross
.endif
BUILDLINK_TREE+= -spirv-cross

# $NetBSD$
BUILDLINK_TREE+= 3dxware-sdk
.if !defined(THREEDXWARE_SDK_BUILDLINK3_MK)
THREEDXWARE_SDK_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.3dxware-sdk+= 3dxware-sdk>=4.0
BUILDLINK_ABI_DEPENDS.3dxware-sdk?= 3dxware-sdk>=4.0
BUILDLINK_PKGSRCDIR.3dxware-sdk?= ../../devel/3dxware-sdk
.endif
BUILDLINK_TREE+= -3dxware-sdk

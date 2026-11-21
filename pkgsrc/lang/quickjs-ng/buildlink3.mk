BUILDLINK_TREE+=	quickjs-ng

.if !defined(QUICKJS_NG_BUILDLINK3_MK)
QUICKJS_NG_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.quickjs-ng+=	quickjs-ng>=0.17.0
BUILDLINK_PKGSRCDIR.quickjs-ng?=	../../lang/quickjs-ng

.endif	# QUICKJS_NG_BUILDLINK3_MK

BUILDLINK_TREE+=	-quickjs-ng

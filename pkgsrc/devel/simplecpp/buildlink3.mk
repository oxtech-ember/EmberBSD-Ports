# Origin: EmberBSD contributors (AI-assisted).
BUILDLINK_TREE+= simplecpp
.if !defined(SIMPLECPP_BUILDLINK3_MK)
SIMPLECPP_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.simplecpp+= simplecpp>=1.9.1
BUILDLINK_PKGSRCDIR.simplecpp?= ../../devel/simplecpp
.endif
BUILDLINK_TREE+= -simplecpp

# Origin: EmberBSD contributors (AI-assisted).
BUILDLINK_TREE+= tcb-span
.if !defined(TCB_SPAN_BUILDLINK3_MK)
TCB_SPAN_BUILDLINK3_MK:=
BUILDLINK_DEPMETHOD.tcb-span?= build
BUILDLINK_API_DEPENDS.tcb-span+= tcb-span>=20220615nb1
BUILDLINK_PKGSRCDIR.tcb-span?= ../../devel/tcb-span
.endif
BUILDLINK_TREE+= -tcb-span

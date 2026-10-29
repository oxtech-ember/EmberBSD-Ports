# Origin: EmberBSD contributors (AI-assisted).
BUILDLINK_TREE+= lief
.if !defined(LIEF_BUILDLINK3_MK)
LIEF_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.lief+= lief>=1.0.0nb1
BUILDLINK_PKGSRCDIR.lief?= ../../devel/lief
.include "../../devel/tl-expected/buildlink3.mk"
.include "../../devel/tcb-span/buildlink3.mk"
.endif
BUILDLINK_TREE+= -lief

# Origin: EmberBSD contributors (AI-assisted).
BUILDLINK_TREE+= lief
.if !defined(LIEF_BUILDLINK3_MK)
LIEF_BUILDLINK3_MK:=
.include "../../mk/bsd.fast.prefs.mk"
BUILDLINK_API_DEPENDS.lief+= lief>=1.0.0nb1
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
BUILDLINK_ABI_DEPENDS.lief+= lief>=1.0.0nb2
.endif
BUILDLINK_PKGSRCDIR.lief?= ../../devel/lief
.include "../../devel/tl-expected/buildlink3.mk"
.include "../../devel/tcb-span/buildlink3.mk"
.endif
BUILDLINK_TREE+= -lief

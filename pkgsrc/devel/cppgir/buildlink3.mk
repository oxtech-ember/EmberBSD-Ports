BUILDLINK_TREE+= cppgir
.if !defined(CPPGIR_BUILDLINK3_MK)
CPPGIR_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.cppgir+= cppgir>=2.0.0
BUILDLINK_PKGSRCDIR.cppgir?= ../../devel/cppgir
.endif
BUILDLINK_TREE+= -cppgir

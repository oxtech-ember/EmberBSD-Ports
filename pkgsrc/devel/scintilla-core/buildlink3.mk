# $NetBSD$
BUILDLINK_TREE+=	scintilla-core
.if !defined(SCINTILLA_CORE_BUILDLINK3_MK)
SCINTILLA_CORE_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.scintilla-core+=	scintilla-core>=5.6.9
BUILDLINK_DEPMETHOD.scintilla-core?=	build
BUILDLINK_PKGSRCDIR.scintilla-core?=	../../devel/scintilla-core
.include "../../mk/pthread.buildlink3.mk"
.endif
BUILDLINK_TREE+=	-scintilla-core

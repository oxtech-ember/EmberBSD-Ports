# $NetBSD$
BUILDLINK_TREE+=	lexilla
.if !defined(LEXILLA_BUILDLINK3_MK)
LEXILLA_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.lexilla+=	lexilla>=5.5.5
BUILDLINK_PKGSRCDIR.lexilla?=	../../devel/lexilla
.include "../../devel/scintilla-core/buildlink3.mk"
.endif
BUILDLINK_TREE+=	-lexilla

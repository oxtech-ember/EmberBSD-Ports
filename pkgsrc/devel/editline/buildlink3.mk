# $NetBSD: buildlink3.mk,v 1.6 2023/06/26 11:37:07 wiz Exp $

BUILDLINK_TREE+=	editline

.if !defined(EDITLINE_BUILDLINK3_MK)
EDITLINE_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.editline+=	editline>=3.1.20260512
BUILDLINK_PKGSRCDIR.editline?=		../../devel/editline
BUILDLINK_INCDIRS.editline?=		include/readline

BUILDLINK_FILES.editline+=	include/history.h
BUILDLINK_FILES.editline+=	include/readline.h

BUILDLINK_FNAME_TRANSFORM.editline+=	-e 's|include/editline/history\.h|include/readline/history.h|g'
BUILDLINK_FNAME_TRANSFORM.editline+=	-e 's|include/editline/readline\.h|include/readline/readline.h|g'

CHECK_BUILTIN.editline:=	yes
.include "../../devel/editline/builtin.mk"
CHECK_BUILTIN.editline:=	no

# A built-in editline is always going to use a built-in termcap.
.if ${USE_BUILTIN.editline:U:tl} == yes
USE_BUILTIN.termcap=	yes
.endif

.if ${USE_BUILTIN.editline:U:tl} == yes
.include "../../mk/termcap.buildlink3.mk"
.else
BUILDLINK_API_DEPENDS.ncurses+=	ncurses>=6.6
.include "../../devel/ncurses/buildlink3.mk"
.endif
.endif	# EDITLINE_BUILDLINK3_MK

BUILDLINK_TREE+=	-editline

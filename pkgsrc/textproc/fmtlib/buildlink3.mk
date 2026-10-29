# $NetBSD: buildlink3.mk,v 1.1 2026/10/19 00:00:00 emberbsd Exp $

BUILDLINK_TREE+=	fmtlib

.if !defined(FMTLIB_BUILDLINK3_MK)
FMTLIB_BUILDLINK3_MK:=

.include "../../mk/bsd.fast.prefs.mk"
BUILDLINK_API_DEPENDS.fmtlib+=	fmtlib>=12.2.0
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
BUILDLINK_ABI_DEPENDS.fmtlib+= fmtlib>=12.2.0nb1
.endif
BUILDLINK_ABI_DEPENDS.fmtlib+=	fmtlib>=12.2.0
BUILDLINK_PKGSRCDIR.fmtlib?=	../../textproc/fmtlib
.endif	# FMTLIB_BUILDLINK3_MK

BUILDLINK_TREE+=	-fmtlib

# $NetBSD: buildlink3.mk,v 1.1 2025/07/27 09:17:06 wiz Exp $

BUILDLINK_TREE+=	tcl

.if !defined(TCL_BUILDLINK3_MK)
TCL_BUILDLINK3_MK:=

.include "../../lang/tcl/Makefile.version"
BUILDLINK_API_DEPENDS.tcl+=	tcl>=${TCL_VERSION}
BUILDLINK_ABI_DEPENDS.tcl+=	tcl>=${TCL_VERSION}
BUILDLINK_PKGSRCDIR.tcl?=	../../lang/tcl


BUILDLINK_FILES.tcl+=	bin/tclsh*
#
# Make "-ltcl" resolve into "-ltcl9.1", so that we don't
# need to patch so many Makefiles.
#
BUILDLINK_TRANSFORM+=	l:tcl:tcl${TCL_BASEVER}


_TOOLS_USE_PKGSRC.tclsh=	yes

TCLCONFIG_SH?=		${BUILDLINK_PREFIX.tcl}/lib/tclConfig.sh
TCLSH=			${BUILDLINK_PREFIX.tcl}/bin/tclsh
.include "../../devel/zlib/buildlink3.mk"
.include "../../mk/dlopen.buildlink3.mk"
.endif # TCL_BUILDLINK3_MK

BUILDLINK_TREE+=	-tcl

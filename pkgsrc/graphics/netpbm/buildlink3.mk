# $NetBSD: buildlink3.mk,v 1.25 2025/08/30 22:45:28 wiz Exp $

BUILDLINK_TREE+=	netpbm

.if !defined(NETPBM_BUILDLINK3_MK)
NETPBM_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.netpbm+=	netpbm>=10.11.6
BUILDLINK_ABI_DEPENDS.netpbm+=	netpbm>=11.02.09nb7
BUILDLINK_PKGSRCDIR.netpbm?=	../../graphics/netpbm

.include "../../mk/bsd.fast.prefs.mk"
# Static consumers also need the loader library used by dictionary lookup.
.if !empty(OPSYS:MDarwin) || !empty(OPSYS:MNetBSD) || !empty(OPSYS:MLinux)
.include "../../mk/dlopen.buildlink3.mk"
BUILDLINK_LDFLAGS.netpbm+=	${DL_LDFLAGS}
BUILDLINK_LIBS.netpbm+=		${DL_LIBS} ${BUILDLINK_LDADD.dl}
.endif

.include "../../graphics/png/buildlink3.mk"
.include "../../graphics/tiff/buildlink3.mk"
.endif # NETPBM_BUILDLINK3_MK

BUILDLINK_TREE+=	-netpbm

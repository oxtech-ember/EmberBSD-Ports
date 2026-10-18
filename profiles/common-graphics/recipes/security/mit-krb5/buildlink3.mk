# $NetBSD: buildlink3.mk,v 1.18 2024/01/05 23:46:29 adam Exp $

BUILDLINK_TREE+=	mit-krb5

.if !defined(MIT_KRB5_BUILDLINK3_MK)
MIT_KRB5_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.mit-krb5+=	mit-krb5>=1.22.2
BUILDLINK_ABI_DEPENDS.mit-krb5+=	mit-krb5>=1.22.2nb1
BUILDLINK_PKGSRCDIR.mit-krb5?=		../../security/mit-krb5
.include "../../mk/bsd.fast.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD"
.include "../../security/mit-krb5-devel/buildlink3.mk"
.endif
.endif # MIT_KRB5_BUILDLINK3_MK

BUILDLINK_TREE+=	-mit-krb5

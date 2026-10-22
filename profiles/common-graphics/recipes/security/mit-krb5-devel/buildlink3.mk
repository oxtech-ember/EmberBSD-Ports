# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Build-only target SDK dependency.
BUILDLINK_TREE+= mit-krb5-devel
.if !defined(MIT_KRB5_DEVEL_BUILDLINK3_MK)
MIT_KRB5_DEVEL_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.mit-krb5-devel+= mit-krb5-devel>=1.22.2nb3
BUILDLINK_ABI_DEPENDS.mit-krb5-devel+= mit-krb5-devel>=1.22.2nb3
BUILDLINK_PKGSRCDIR.mit-krb5-devel?= ../../security/mit-krb5-devel
BUILDLINK_DEPMETHOD.mit-krb5-devel= build
BUILDLINK_CONTENTS_FILTER.mit-krb5-devel= ${CAT}
.endif
BUILDLINK_TREE+= -mit-krb5-devel

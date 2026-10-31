# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Build-only target SDK dependency.
BUILDLINK_TREE+= icu-devel
.if !defined(ICU_DEVEL_BUILDLINK3_MK)
ICU_DEVEL_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.icu-devel+= icu-devel>=79.1nb1
BUILDLINK_ABI_DEPENDS.icu-devel+= icu-devel>=79.1nb1
BUILDLINK_PKGSRCDIR.icu-devel?= ../../textproc/icu-devel
BUILDLINK_DEPMETHOD.icu-devel= build
BUILDLINK_CONTENTS_FILTER.icu-devel= ${CAT}
.endif
BUILDLINK_TREE+= -icu-devel

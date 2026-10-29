# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Target generators stay in the host SDK.
BUILDLINK_TREE+=	protobuf-devel
.if !defined(PROTOBUF_DEVEL_BUILDLINK3_MK)
PROTOBUF_DEVEL_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.protobuf-devel+=	protobuf-devel>=36.2nb3
BUILDLINK_ABI_DEPENDS.protobuf-devel+=	protobuf-devel>=36.2nb2
BUILDLINK_PKGSRCDIR.protobuf-devel?=	../../devel/protobuf-devel
BUILDLINK_DEPMETHOD.protobuf-devel=	build
# CMake checks every imported target, including the target-side generators.
BUILDLINK_CONTENTS_FILTER.protobuf-devel=	${CAT}
.endif
BUILDLINK_TREE+=	-protobuf-devel

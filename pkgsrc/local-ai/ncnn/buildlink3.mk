# SPDX-License-Identifier: MIT
BUILDLINK_TREE+= ncnn
.if !defined(NCNN_BUILDLINK3_MK)
NCNN_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.ncnn+= ncnn>=20260526
BUILDLINK_ABI_DEPENDS.ncnn+= ncnn>=20260526
BUILDLINK_PKGSRCDIR.ncnn?= ../../local-ai/ncnn
.include "../../mk/pthread.buildlink3.mk"
.endif
BUILDLINK_TREE+= -ncnn

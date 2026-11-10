# SPDX-License-Identifier: MIT
BUILDLINK_TREE+= onnxruntime
.if !defined(ONNXRUNTIME_BUILDLINK3_MK)
ONNXRUNTIME_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.onnxruntime+= onnxruntime>=1.31.0
BUILDLINK_ABI_DEPENDS.onnxruntime+= onnxruntime>=1.31.0
BUILDLINK_PKGSRCDIR.onnxruntime?= ../../local-ai/onnxruntime
.endif
BUILDLINK_TREE+= -onnxruntime

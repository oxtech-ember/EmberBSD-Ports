# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Target SDK files are build-only dependencies.
BUILDLINK_TREE+= llvm-devel
.if !defined(LLVM_DEVEL_BUILDLINK3_MK)
LLVM_DEVEL_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.llvm-devel+= llvm-devel>=23.1.3nb1
BUILDLINK_ABI_DEPENDS.llvm-devel+= llvm-devel>=23.1.3nb1
BUILDLINK_PKGSRCDIR.llvm-devel?= ../../lang/llvm-devel
BUILDLINK_DEPMETHOD.llvm-devel= build
# Preserve tools, headers, static archives and every imported CMake target.
BUILDLINK_CONTENTS_FILTER.llvm-devel= ${CAT}
.endif
BUILDLINK_TREE+= -llvm-devel

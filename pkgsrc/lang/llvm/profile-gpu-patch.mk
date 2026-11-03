# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Share the checked compiler-rt profile patch.
.if !defined(_EMBERBSD_LLVM_REUSE) && !defined(_EMBERBSD_LLVM_SHARED_DEVEL)
post-patch:
	${TOOL_PYTHONBIN:Q} -B ${PKGSRCDIR:Q}/lang/compiler-rt/files/apply-profile-gpu-patch.py \
	    --patch-file ${PKGSRCDIR:Q}/lang/compiler-rt/patches/patch-13-profile-gpu-bounds \
	    --distinfo ${PKGSRCDIR:Q}/lang/compiler-rt/distinfo --patch-tool ${PATCH:Q} \
	    --workdir ${WRKSRC:Q}/include/llvm/ProfileData
.endif

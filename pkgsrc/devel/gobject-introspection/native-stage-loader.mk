# SPDX-License-Identifier: BSD-2-Clause
# Preserve a selected native replacement runtime after package-local paths.
.if !defined(EMBERBSD_NATIVE_STAGE_LOADER_MK)
EMBERBSD_NATIVE_STAGE_LOADER_MK:=
_EMBERBSD_NATIVE_RUNTIME_SUFFIX=
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && !empty(EMBERBSD_NATIVE_STAGE_ROOT:U) && !empty(EMBERBSD_NATIVE_RUNTIME_VIEW:U)
.  if empty(EMBERBSD_NATIVE_RUNTIME_VIEW:M/*) || !empty(EMBERBSD_NATIVE_RUNTIME_VIEW:C/[A-Za-z0-9_.\/+@%=-]//g) || !exists(${EMBERBSD_NATIVE_RUNTIME_VIEW}/.)
.    error EMBERBSD_NATIVE_RUNTIME_VIEW must be an absolute existing directory without colon
.  endif
_EMBERBSD_NATIVE_RUNTIME_SUFFIX= :${EMBERBSD_NATIVE_RUNTIME_VIEW:Q}
.endif

.if !empty(_EMBERBSD_NATIVE_RUNTIME_SUFFIX)
MAKE_ENV+= EMBERBSD_NATIVE_RUNTIME_VIEW=${EMBERBSD_NATIVE_RUNTIME_VIEW:Q}
.endif

.endif # EMBERBSD_NATIVE_STAGE_LOADER_MK

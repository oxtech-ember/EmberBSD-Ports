# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Upstream native tool sub-configure inputs.
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
CONFIGURE_ARGS+= --build=${NATIVE_MACHINE_GNU_PLATFORM:Q}
CONFIGURE_ARGS+= --host=${MACHINE_GNU_PLATFORM:Q}
# The common SDK command contains ABI flags; pass the executable and flags
# separately so the nested configure sees each argument exactly once.
.if defined(EMBERBSD_CROSS_BUILD_CC)
CONFIGURE_ENV+= BUILD_CC=${EMBERBSD_CROSS_BUILD_CC:Q}
.else
CONFIGURE_ENV+= BUILD_CC=${NATIVE_CC:Q}
.endif
CONFIGURE_ENV+= BUILD_AR=${NATIVE_AR:Q}
CONFIGURE_ENV+= BUILD_RANLIB=${NATIVE_RANLIB:Q}
.endif

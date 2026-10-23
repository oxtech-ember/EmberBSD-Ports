# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Upstream native tool sub-configure inputs.
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
CONFIGURE_ARGS+= --build=${NATIVE_MACHINE_GNU_PLATFORM:Q}
CONFIGURE_ARGS+= --host=${MACHINE_GNU_PLATFORM:Q}
CONFIGURE_ENV+= BUILD_CC=${NATIVE_CC:Q}
CONFIGURE_ENV+= BUILD_AR=${NATIVE_AR:Q}
CONFIGURE_ENV+= BUILD_RANLIB=${NATIVE_RANLIB:Q}
.endif

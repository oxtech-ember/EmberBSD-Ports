# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Shared Autosetup cross-tool routing.
.if ${USE_CROSS_COMPILE:tl} == "yes"
CONFIGURE_ARGS+=	--build=${NATIVE_MACHINE_GNU_PLATFORM:Q}
CONFIGURE_ARGS+=	--host=${MACHINE_GNU_PLATFORM:S/--/-unknown-/:Q}
CONFIGURE_ENV+=		CC_FOR_BUILD=${TOOLS_CMD.native-cc:Q}
TOOLS_CREATE+=		native-cc
TOOLS_SCRIPT.native-cc=	exec ${NATIVE_CC} "$$@"
.endif

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
# Override only target libtool; native secondary configure owns tools/tta/libtool.
LIBTOOL_OVERRIDE= tta/libtool tta/perl/CheckXS/libtool
# Keep native recursive tools separate from the target compiler wrappers.
.if defined(EMBERBSD_NATIVE_TOOLSET_MAKECONF)
_TEXINFO_HOST_ALIASES= ${WRKDIR}/.texinfo-native-tools
CONFIGURE_ENV+= PATH_FOR_BUILD=${_TEXINFO_HOST_ALIASES:Q}:${TOOLBASE:Q}/bin:${TOOLBASE:Q}/gnu/bin
CONFIGURE_ENV+= MAKE_FOR_BUILD=${TOOLS_PATH.gmake:Q}
CONFIGURE_ENV+= PERL_EXT_CC_FOR_BUILD=${EMBERBSD_CROSS_BUILD_CC:Q}
CONFIGURE_ENV+= PREFIX_FOR_BUILD=${TOOLBASE:Q}
CONFIGURE_ENV+= LD_FOR_BUILD=${EMBERBSD_CROSS_BUILD_LD:Q}
CONFIGURE_ENV+= CFLAGS_FOR_BUILD=${HOST_CFLAGS:Q}
CONFIGURE_ENV+= LDFLAGS_FOR_BUILD=${HOST_LDFLAGS:Q}\ -L${TOOLBASE:Q}/lib
CONFIGURE_ENV+= CPPFLAGS_FOR_BUILD=${HOST_CPPFLAGS:Q}\ -I${TOOLBASE:Q}/include\ -DPKGSRC_INFOPATH=\\\"${TOOLBASE}/${PKGINFODIR}\\\"
.PHONY: texinfo-native-aliases
texinfo-native-aliases:
	${RUN}${EMBERBSD_CROSS_BUILD_PYTHON:Q} -B ${PKGSRCDIR}/prepare-native-tools.py \
	    --sdk-source ${EMBERBSD_SDK_SOURCE:Q} aliases --host-prefix ${TOOLBASE:Q} \
	    --compiler-family ${EMBERBSD_HOST_COMPILER_FAMILY:Q} --output ${_TEXINFO_HOST_ALIASES:Q}
pre-configure: texinfo-native-aliases
.endif

.endif

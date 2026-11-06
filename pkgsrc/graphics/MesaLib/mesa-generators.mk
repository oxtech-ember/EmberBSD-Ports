# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted). Use real native Mesa generators.
_EMBERBSD_MESA_NATIVE= ${WRKDIR}/.meson-generators-native
MESON_NATIVE_ARGS+= --native-file ${_EMBERBSD_MESA_NATIVE:Q}
USE_TOOLS+= cmp
pre-configure: emberbsd-mesa-generators-check ${_EMBERBSD_MESA_NATIVE}
.PHONY: emberbsd-mesa-generators-check ${_EMBERBSD_MESA_NATIVE}

.if !empty(EMBERBSD_MESA_GENERATORS:U)
# Explicit external seals retain the standalone producer's ABI and hash checks.
USE_TOOLS+= digest
_EMBERBSD_MESA_GENERATOR_BINDIR= ${EMBERBSD_MESA_GENERATORS}/bin
emberbsd-mesa-generators-check:
	${RUN} ember_mesa_generators=${EMBERBSD_MESA_GENERATORS:Q}; \
	case "$$ember_mesa_generators" in /*) ;; \
	*) echo 'External shader tools require an absolute sealed directory' >&2; exit 1;; esac; \
	case "$$ember_mesa_generators" in *[!A-Za-z0-9_./-]*) \
	    echo 'External shader tools require a path without whitespace or shell metacharacters' >&2; exit 1;; esac; \
	test -f "$$ember_mesa_generators/installed.sha256" || { \
	    echo 'External shader tools require an installed.sha256 seal' >&2; exit 1; \
	}; \
	${SH} ${.CURDIR}/verify-mesa-generators.sh ${TOOLS_DIGEST:Q} \
	    "$$ember_mesa_generators" ${WRKSRC:Q} ${_EMBERBSD_MESA_GENERATOR_PROFILES:O:u:ts,:Q}

.else
TOOL_DEPENDS+= mesa-generators-${MESA_GENERATORS_VERSION}:../mesa-generators
_EMBERBSD_MESA_GENERATOR_BINDIR= ${TOOLBASE}/bin
.for generator in ${_EMBERBSD_MESA_GENERATOR_NAMES:O:u}
TOOLS_PATH.${generator}= ${TOOLBASE}/bin/${generator}
.endfor
emberbsd-mesa-generators-check:
.for generator in ${_EMBERBSD_MESA_GENERATOR_NAMES:O:u}
	${TEST} -x ${TOOLS_PATH.${generator}:Q}
.endfor
.endif

# Selection can change in a retained workdir. Keep the timestamp when it does not.
${_EMBERBSD_MESA_NATIVE}:
	${RUN}${ECHO} '[binaries]' > ${.TARGET:Q}.tmp
.for generator in ${_EMBERBSD_MESA_GENERATOR_NAMES:O:u}
	${RUN}${ECHO} "${generator} = '${_EMBERBSD_MESA_GENERATOR_BINDIR}/${generator}'" >> ${.TARGET:Q}.tmp
.endfor
	${RUN}if ${CMP} -s ${.TARGET:Q}.tmp ${.TARGET:Q}; then \
	    ${RM} -f ${.TARGET:Q}.tmp; \
	else ${MV} -f ${.TARGET:Q}.tmp ${.TARGET:Q}; fi

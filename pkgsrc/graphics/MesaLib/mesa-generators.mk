# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted). Use real native Mesa generators.
USE_TOOLS+= digest
_EMBERBSD_MESA_NATIVE= ${WRKDIR}/.meson-generators-native
MESON_NATIVE_ARGS+= --native-file ${_EMBERBSD_MESA_NATIVE:Q}
pre-configure: emberbsd-mesa-generators-check ${_EMBERBSD_MESA_NATIVE}
.PHONY: emberbsd-mesa-generators-check
emberbsd-mesa-generators-check:
	${RUN} ember_mesa_generators=${EMBERBSD_MESA_GENERATORS:U:Q}; \
	case "$$ember_mesa_generators" in /*) ;; \
	*) echo 'Shader generation requires an absolute sealed EMBERBSD_MESA_GENERATORS directory' >&2; exit 1;; esac; \
	case "$$ember_mesa_generators" in *[!A-Za-z0-9_./-]*) \
	    echo 'Shader generation requires a path without whitespace or shell metacharacters' >&2; exit 1;; esac; \
	test -f "$$ember_mesa_generators/installed.sha256" || { \
	    echo 'Shader generation requires an absolute sealed EMBERBSD_MESA_GENERATORS directory' >&2; exit 1; \
	}; \
	${SH} ${.CURDIR}/verify-mesa-generators.sh ${TOOLS_DIGEST:Q} \
	    "$$ember_mesa_generators" ${WRKSRC:Q} ${_EMBERBSD_MESA_GENERATOR_PROFILES:O:u:ts,:Q}

${_EMBERBSD_MESA_NATIVE}:
	${RUN}${ECHO} '[binaries]' > ${.TARGET:Q}.tmp
.for generator in ${_EMBERBSD_MESA_GENERATOR_NAMES:O:u}
	${RUN}${ECHO} "${generator} = '${EMBERBSD_MESA_GENERATORS}/bin/${generator}'" >> ${.TARGET:Q}.tmp
.endfor
	${RUN}${MV} -f ${.TARGET:Q}.tmp ${.TARGET:Q}

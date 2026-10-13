# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted). Use real native Mesa generators.
.if empty(EMBERBSD_MESA_GENERATORS:U:M/*) || \
    !empty(EMBERBSD_MESA_GENERATORS:C/[A-Za-z0-9_.\/-]//g) || \
    !exists(${EMBERBSD_MESA_GENERATORS}/installed.sha256)
PKG_FAIL_REASON+= "PowerVR requires an absolute sealed EMBERBSD_MESA_GENERATORS directory"
.endif
USE_TOOLS+= digest
_EMBERBSD_MESA_NATIVE= ${WRKDIR}/.meson-generators-native
MESON_NATIVE_ARGS+= --native-file ${_EMBERBSD_MESA_NATIVE:Q}
pre-configure: emberbsd-mesa-generators-check ${_EMBERBSD_MESA_NATIVE}
.PHONY: emberbsd-mesa-generators-check
emberbsd-mesa-generators-check:
	${SH} ${.CURDIR}/verify-mesa-generators.sh ${TOOLS_DIGEST:Q} \
	    ${EMBERBSD_MESA_GENERATORS:Q} ${WRKSRC:Q}

${_EMBERBSD_MESA_NATIVE}:
	${RUN}${ECHO} '[binaries]' > ${.TARGET:Q}.tmp
.for generator in mesa_clc vtn_bindgen2 pco_clc
	${RUN}${ECHO} "${generator} = '${EMBERBSD_MESA_GENERATORS}/bin/${generator}'" >> ${.TARGET:Q}.tmp
.endfor
	${RUN}${MV} -f ${.TARGET:Q}.tmp ${.TARGET:Q}

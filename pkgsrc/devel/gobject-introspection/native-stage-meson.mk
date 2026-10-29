# SPDX-License-Identifier: BSD-2-Clause
# This file is included by Meson's native stage path, never generic GI consumers.
.if !empty(EMBERBSD_NATIVE_RUNTIME_VIEW:U)
_MESON_STAGE_GI_ARG= --native-file ${WRKDIR:Q}/.meson-emberbsd-native-gi
MESON_NATIVE_EXTRA_ARGS+= ${BUILDLINK_TREE:Mgobject-introspection:C,^.+$,${_MESON_STAGE_GI_ARG},}
pre-configure: emberbsd-native-gi-meson
.PHONY: emberbsd-native-gi-meson
emberbsd-native-gi-meson:
	${RUN}if ${TEST} -n "${BUILDLINK_TREE:Mgobject-introspection}"; then \
	    ${TEST} -n "${EMBERBSD_NATIVE_STAGE_PYTHON:U:Q}" && ${TEST} -n "${EMBERBSD_SDK_SOURCE:U:Q}" && ${TEST} -n "${EMBERBSD_NATIVE_STAGE_PREFIX:U:Q}" || { ${ERROR_MSG} "Missing native Python, SDK source or stage prefix"; exit 1; }; \
	    case "${EMBERBSD_NATIVE_STAGE_PREFIX:U:Q}" in /*) ;; *) ${ERROR_MSG} "Stage prefix must be absolute"; exit 1;; esac; \
	    for path in ${EMBERBSD_NATIVE_STAGE_PYTHON:U:Q} ${EMBERBSD_SDK_SOURCE:U:Q} ${EMBERBSD_NATIVE_RUNTIME_VIEW:Q} ${EMBERBSD_NATIVE_STAGE_ROOT:Q}${EMBERBSD_NATIVE_STAGE_PREFIX:Q}; do \
	      case "$$path" in /*) ;; *) ${ERROR_MSG} "Select absolute native GI inputs"; exit 1;; esac; \
	      case "$$path" in *[!A-Za-z0-9_./+@%=-]*) ${ERROR_MSG} "Unsafe native GI path"; exit 1;; esac; \
	    done; \
	    ${TEST} -x ${EMBERBSD_NATIVE_STAGE_PYTHON:Q} && ${TEST} -f ${EMBERBSD_SDK_SOURCE:Q}/scripts/run-darwin-with-runtime.py || { ${ERROR_MSG} "Missing native Python or SDK launcher"; exit 1; }; \
	    ${PRINTF} '%s\n' '[binaries]' \
	      "g-ir-scanner = '${EMBERBSD_NATIVE_STAGE_ROOT}${EMBERBSD_NATIVE_STAGE_PREFIX}/bin/g-ir-scanner'" \
	      "g-ir-compiler = ['${EMBERBSD_NATIVE_STAGE_PYTHON}', '${EMBERBSD_SDK_SOURCE}/scripts/run-darwin-with-runtime.py', '--runtime-view', '${EMBERBSD_NATIVE_RUNTIME_VIEW}', '--', '${EMBERBSD_NATIVE_STAGE_ROOT}${EMBERBSD_NATIVE_STAGE_PREFIX}/bin/g-ir-compiler']" > ${WRKDIR:Q}/.meson-emberbsd-native-gi; \
	fi
.endif

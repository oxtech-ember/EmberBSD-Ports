# SPDX-License-Identifier: BSD-2-Clause
# GLib build-machine tools are separate from target pkg-config files.
.if ${USE_CROSS_COMPILE:U:tl} == yes
_MESON_GLIB_TOOLS_PREFIX= ${TOOLBASE}
.else
_MESON_GLIB_TOOLS_PREFIX= ${EMBERBSD_NATIVE_STAGE_ROOT:U}${EMBERBSD_NATIVE_STAGE_PREFIX:U}
.endif
_MESON_STAGE_GLIB_ARG= --native-file ${WRKDIR:Q}/.meson-emberbsd-native-glib
MESON_NATIVE_EXTRA_ARGS+= ${BUILDLINK_TREE:Mglib2:O:u:C,^.+$,${_MESON_STAGE_GLIB_ARG},}
pre-configure: emberbsd-native-glib-meson
.PHONY: emberbsd-native-glib-meson
emberbsd-native-glib-meson:
	${RUN}if ${TEST} -n "${BUILDLINK_TREE:Mglib2}"; then \
	    ${TEST} -n "${_MESON_GLIB_TOOLS_PREFIX:Q}" || { ${ERROR_MSG} "Missing selected GLib tool prefix"; exit 1; }; \
	    for base in ${_MESON_GLIB_TOOLS_PREFIX:Q}; do \
	      case "$$base" in /*) ;; *) ${ERROR_MSG} "Select an absolute GLib tool prefix"; exit 1;; esac; \
	      case "$$base" in *[!A-Za-z0-9_./+@%=-]*) ${ERROR_MSG} "Unsafe GLib tool prefix"; exit 1;; esac; \
	    done; \
	    ${PRINTF} '%s\n' '[binaries]' > ${WRKDIR:Q}/.meson-emberbsd-native-glib; \
	    for tool in glib-mkenums glib-genmarshal glib-compile-resources glib-compile-schemas gdbus-codegen gio-querymodules; do \
	      path=${_MESON_GLIB_TOOLS_PREFIX:Q}/bin/$$tool; \
	      if ${TEST} -x "$$path"; then ${PRINTF} "%s = '%s'\n" "$$tool" "$$path" >> ${WRKDIR:Q}/.meson-emberbsd-native-glib; fi; \
	    done; \
	fi

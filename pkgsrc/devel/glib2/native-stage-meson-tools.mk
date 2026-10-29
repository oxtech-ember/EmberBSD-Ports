# SPDX-License-Identifier: BSD-2-Clause
# GLib host tools have a separate package from its staged pkg-config files.
_MESON_STAGE_GLIB_ARG= --native-file ${WRKDIR:Q}/.meson-emberbsd-native-glib
MESON_NATIVE_EXTRA_ARGS+= ${BUILDLINK_TREE:Mglib2:C,^.+$,${_MESON_STAGE_GLIB_ARG},}
pre-configure: emberbsd-native-glib-meson
.PHONY: emberbsd-native-glib-meson
emberbsd-native-glib-meson:
	${RUN}if ${TEST} -n "${BUILDLINK_TREE:Mglib2}"; then \
	    ${TEST} -n "${EMBERBSD_NATIVE_STAGE_ROOT:U:Q}" && ${TEST} -n "${EMBERBSD_NATIVE_STAGE_PREFIX:U:Q}" || { ${ERROR_MSG} "Missing native GLib stage paths"; exit 1; }; \
	    for base in ${EMBERBSD_NATIVE_STAGE_ROOT:U:Q} ${EMBERBSD_NATIVE_STAGE_PREFIX:U:Q}; do \
	      case "$$base" in /*) ;; *) ${ERROR_MSG} "Select absolute native GLib stage paths"; exit 1;; esac; \
	      case "$$base" in *[!A-Za-z0-9_./+@%=-]*) ${ERROR_MSG} "Unsafe native GLib stage path"; exit 1;; esac; \
	    done; \
	    ${PRINTF} '%s\n' '[binaries]' > ${WRKDIR:Q}/.meson-emberbsd-native-glib; \
	    for tool in glib-mkenums glib-genmarshal glib-compile-resources gdbus-codegen glib-compile-schemas gio-querymodules; do \
	      path=${EMBERBSD_NATIVE_STAGE_ROOT:Q}${EMBERBSD_NATIVE_STAGE_PREFIX:Q}/bin/$$tool; \
	      if ${TEST} -x "$$path"; then ${PRINTF} "%s = '%s'\n" "$$tool" "$$path" >> ${WRKDIR:Q}/.meson-emberbsd-native-glib; fi; \
	    done; \
	fi

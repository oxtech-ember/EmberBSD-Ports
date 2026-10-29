# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), native generators with real target GType queries.
.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
.if ${MACHINE_ARCH:U} == "aarch64"
_EMBER_GI_TARGET= aarch64
_EMBER_GI_TRIPLET= aarch64--netbsd
.elif ${MACHINE_ARCH:U} == "x86_64"
_EMBER_GI_TARGET= amd64
_EMBER_GI_TRIPLET= x86_64--netbsd
.else
PKG_FAIL_REASON+= "The GI cross recipe supports only aarch64 and x86_64"
.endif
.if ${OPSYS:U} != "NetBSD" || ${CROSS_OPSYS:U} != "NetBSD" || \
    empty(CROSS_OS_VERSION:M11.*) || "${CROSS_MACHINE_ARCH:U}" != "${MACHINE_ARCH:U}" || \
    "${MACHINE_GNU_PLATFORM:U}" != "${_EMBER_GI_TRIPLET:U}" || \
    "${EMBERBSD_CROSS_TARGET:U${_EMBER_GI_TARGET:U}}" != "${_EMBER_GI_TARGET:U}"
PKG_FAIL_REASON+= "GI requires matching NetBSD 11 target, architecture and GNU provider metadata"
.endif
# Keep the published GI selector compatible with the common Python provider.
.if defined(EMBERBSD_GI_PYTHON)
.if defined(EMBERBSD_CROSS_BUILD_PYTHON) && "${EMBERBSD_CROSS_BUILD_PYTHON}" != "${EMBERBSD_GI_PYTHON}"
PKG_FAIL_REASON+= "GI and common build tools must select the same Python provider"
.else
EMBERBSD_CROSS_BUILD_PYTHON?= ${EMBERBSD_GI_PYTHON}
.endif
.endif
# Introspection dumps: replay the recipe's stored dumps (default), query a
# live EmberBSD target, or query it and capture the dumps
# (profiles/common-graphics/cross/gi-dumps.md). Recipes that also execute
# target programs set EMBERBSD_GI_EXECUTE=yes and always need the query.
EMBERBSD_GI_DUMP_MODE?= replay
_EMBER_GI_PLATFORM= ${CROSS_OPSYS}-${CROSS_OS_VERSION}-${MACHINE_ARCH}
EMBERBSD_GI_DUMP_DIR= ${PKGDIR}/files/gi-dump/${_EMBER_GI_PLATFORM}
_EMBER_GI_INPUTS= EMBERBSD_CROSS_BUILD_PYTHON EMBERBSD_CROSS_BUILD_CC
.if "${EMBERBSD_GI_DUMP_MODE}" != "replay" || ${EMBERBSD_GI_EXECUTE:Uno:tl} == "yes"
_EMBER_GI_INPUTS+= EMBERBSD_GI_QUERY_CONFIG
.endif
# Fetch, checksum and extract do not use these build-host inputs, so they
# are checked when configure starts instead of refusing the whole package.
_EMBER_GI_INPUT_ERRORS=
.if "${EMBERBSD_GI_DUMP_MODE}" != "replay" && "${EMBERBSD_GI_DUMP_MODE}" != "live" && "${EMBERBSD_GI_DUMP_MODE}" != "capture"
_EMBER_GI_INPUT_ERRORS+= EMBERBSD_GI_DUMP_MODE
.endif
.if "${EMBERBSD_GI_DUMP_MODE}" == "capture" && (empty(EMBERBSD_GI_DUMP_CAPTURE_DIR:M/*) || \
    !empty(EMBERBSD_GI_DUMP_CAPTURE_DIR:C/[A-Za-z0-9_.\/-]//g) || !exists(${EMBERBSD_GI_DUMP_CAPTURE_DIR}/.))
_EMBER_GI_INPUT_ERRORS+= EMBERBSD_GI_DUMP_CAPTURE_DIR
.endif
.for _input in ${_EMBER_GI_INPUTS}
.if empty(${_input}:M/*) || !empty(${_input}:C/[A-Za-z0-9_.\/-]//g) || !exists(${${_input}})
_EMBER_GI_INPUT_ERRORS+= ${_input}
.endif
.endfor
.if empty(EMBERBSD_SDK_SOURCE:M/*) || !empty(EMBERBSD_SDK_SOURCE:C/[A-Za-z0-9_.\/-]//g) || !exists(${EMBERBSD_SDK_SOURCE}/src/emberbsd_sdk/__init__.py)
_EMBER_GI_INPUT_ERRORS+= EMBERBSD_SDK_SOURCE
.endif
pre-configure: emberbsd-gi-inputs
.PHONY: emberbsd-gi-inputs
emberbsd-gi-inputs:
.for _input in ${_EMBER_GI_INPUT_ERRORS}
.if ${_input} == "EMBERBSD_SDK_SOURCE"
	@${ERROR_MSG} "EMBERBSD_SDK_SOURCE must name an absolute SDK source directory without shell metacharacters"
.elif ${_input} == "EMBERBSD_GI_DUMP_MODE"
	@${ERROR_MSG} "EMBERBSD_GI_DUMP_MODE must be replay, live or capture"
.elif ${_input} == "EMBERBSD_GI_DUMP_CAPTURE_DIR"
	@${ERROR_MSG} "EMBERBSD_GI_DUMP_CAPTURE_DIR must name an existing absolute directory without shell metacharacters"
.else
	@${ERROR_MSG} "${_input} must name an existing absolute file without shell metacharacters"
.endif
.endfor
.if !empty(_EMBER_GI_INPUT_ERRORS)
	@${FALSE}
.endif
# Cross dependency traversal builds the native tool package independently.
TOOL_DEPENDS+= gobject-introspection>=1.86.0nb4:../../devel/gobject-introspection
EMBERBSD_GI_FILESDIR?= ${.CURDIR}/../../devel/gobject-introspection/files
# Consumers share the launcher and native machine file, but not GI's options.
.if ${EMBERBSD_GI_MESON_OPTIONS:Uyes:tl} == "yes"
MESON_ARGS+= -Dgi_cross_use_prebuilt_gi=true
MESON_ARGS+= -Dgi_cross_ldd_wrapper=${EMBERBSD_GI_FILESDIR}/elf-needed.sh
.endif
MAKE_ENV+= GI_CROSS_LAUNCHER=${EMBERBSD_CROSS_BUILD_PYTHON:Q}\ -E\ -S\ ${EMBERBSD_GI_FILESDIR:Q}/target-query.py
MAKE_ENV+= EMBERBSD_SDK_SOURCE=${EMBERBSD_SDK_SOURCE:Q}
MAKE_ENV+= EMBERBSD_GI_QUERY_CONFIG=${EMBERBSD_GI_QUERY_CONFIG:Q}
MAKE_ENV+= EMBERBSD_GI_TARGET=${_EMBER_GI_TARGET:Q}
MAKE_ENV+= EMBERBSD_GI_READELF=${TOOLDIR:Q}/bin/${_EMBER_GI_TRIPLET}-readelf
_EMBER_GI_DUMP_ENV= EMBERBSD_GI_DUMP_MODE=${EMBERBSD_GI_DUMP_MODE:Q}
_EMBER_GI_DUMP_ENV+= EMBERBSD_GI_DUMP_PLATFORM=${_EMBER_GI_PLATFORM:Q}
_EMBER_GI_DUMP_ENV+= EMBERBSD_GI_DUMP_RECIPE=${PKGPATH:Q}
_EMBER_GI_DUMP_ENV+= EMBERBSD_GI_DUMP_PACKAGE=${PKGNAME_NOREV:Q}
_EMBER_GI_DUMP_ENV+= EMBERBSD_GI_DUMP_DIR=${EMBERBSD_GI_DUMP_DIR:Q}
_EMBER_GI_DUMP_ENV+= EMBERBSD_GI_DUMP_CAPTURE_DIR=${EMBERBSD_GI_DUMP_CAPTURE_DIR:Q}
MAKE_ENV+= ${_EMBER_GI_DUMP_ENV}
MESON_NATIVE_ARGS+= --native-file ${WRKDIR}/.meson-gi-native
# Meson consumers can replace DYLD_LIBRARY_PATH for target artifacts. Keep the
# selected native GI runtime available to the compiler and scanner on Darwin.
_EMBER_GI_COMPILER= ${TOOLBASE}/bin/g-ir-compiler
.if ${NATIVE_OPSYS:U} == "Darwin" && !empty(EMBERBSD_NATIVE_RUNTIME_VIEW:U)
_EMBER_GI_COMPILER= ${WRKDIR}/.meson-gi-compiler
MAKE_ENV+= EMBERBSD_NATIVE_RUNTIME_VIEW=${EMBERBSD_NATIVE_RUNTIME_VIEW:Q}
.endif
MESON_BINARIES+= pkg-config
MESON_BINARY.pkg-config= ${WRKDIR}/.meson-gi-pkg-config

pre-configure: emberbsd-gi-native
.PHONY: emberbsd-gi-native
emberbsd-gi-native: emberbsd-gi-inputs
.if "${EMBERBSD_GI_DUMP_MODE}" == "replay"
	${RUN}${TEST} -d ${EMBERBSD_GI_DUMP_DIR:Q} || { ${ERROR_MSG} "No stored GI dumps for ${_EMBER_GI_PLATFORM} in ${PKGPATH}; capture them from an EmberBSD target (profiles/common-graphics/cross/gi-dumps.md)"; exit 1; }
.else
	${RUN}${SETENV} EMBERBSD_SDK_SOURCE=${EMBERBSD_SDK_SOURCE:Q} EMBERBSD_GI_QUERY_CONFIG=${EMBERBSD_GI_QUERY_CONFIG:Q} ${EMBERBSD_CROSS_BUILD_PYTHON} -E -S ${EMBERBSD_GI_FILESDIR}/target-query.py --check ${WRKDIR} ${CROSS_DESTDIR} ${TOOLDIR}/bin/${_EMBER_GI_TRIPLET}-readelf ${_EMBER_GI_TARGET}
.endif
	${RUN}${TEST} -x ${TOOLBASE}/bin/g-ir-scanner && ${TEST} -x ${TOOLBASE}/bin/g-ir-compiler
	${RUN}version=$$(env PKG_CONFIG_SYSROOT_DIR= PKG_CONFIG_PATH= PKG_CONFIG_LIBDIR=${TOOLBASE}/lib/pkgconfig:${TOOLBASE}/share/pkgconfig ${TOOLBASE}/bin/pkg-config --modversion gobject-introspection-1.0); ${TEST} "$$version" = 1.86.0
.if ${NATIVE_OPSYS:U} == "Darwin" && !empty(EMBERBSD_NATIVE_RUNTIME_VIEW:U)
	${RUN}for path in ${EMBERBSD_CROSS_BUILD_PYTHON:Q} ${EMBERBSD_SDK_SOURCE:Q} ${EMBERBSD_NATIVE_RUNTIME_VIEW:Q} ${TOOLBASE:Q}; do \
	    case "$$path" in /*) ;; *) ${ERROR_MSG} "Select absolute native GI inputs"; exit 1;; esac; \
	    case "$$path" in *[!A-Za-z0-9_./+@%=\ -]*) ${ERROR_MSG} "Unsafe native GI path"; exit 1;; esac; \
	done
	${RUN}${TEST} -x ${EMBERBSD_CROSS_BUILD_PYTHON:Q} && ${TEST} -d ${EMBERBSD_NATIVE_RUNTIME_VIEW:Q} && ${TEST} -f ${EMBERBSD_SDK_SOURCE:Q}/scripts/run-darwin-with-runtime.py
	${RUN}${PRINTF} '%s\n' '#!${TOOLS_SHELL}' \
	    'exec "${EMBERBSD_CROSS_BUILD_PYTHON}" -E -S "${EMBERBSD_SDK_SOURCE}/scripts/run-darwin-with-runtime.py" --runtime-view "${EMBERBSD_NATIVE_RUNTIME_VIEW}" -- "${TOOLBASE}/bin/g-ir-compiler" "$$@"' > ${_EMBER_GI_COMPILER:Q}
	${RUN}${CHMOD} +x ${_EMBER_GI_COMPILER:Q}
.endif
	${RUN}${SED} \
	    -e 's|@PKG_CONFIG@|${TOOLS_CMD.pkg-config}|g' \
	    -e 's|@GI_SCANNER@|${WRKDIR}/.meson-gi-scanner|g' \
	    -e 's|@GI_COMPILER@|${_EMBER_GI_COMPILER}|g' \
	    ${EMBERBSD_GI_FILESDIR}/target-pkg-config.sh > ${WRKDIR}/.meson-gi-pkg-config
	${RUN}${CHMOD} +x ${WRKDIR}/.meson-gi-pkg-config
	${RUN}${SED} \
	    -e 's|@GI_SCANNER@|${TOOLBASE}/bin/g-ir-scanner|g' \
	    -e 's|@GI_LDD_WRAPPER@|${EMBERBSD_GI_FILESDIR}/elf-needed.sh|g' \
	    ${EMBERBSD_GI_FILESDIR}/target-gir-scanner.sh > ${WRKDIR}/.meson-gi-scanner
	${RUN}${CHMOD} +x ${WRKDIR}/.meson-gi-scanner
	${RUN}${PRINTF} '%s\n' '[binaries]' \
	    "c = '${EMBERBSD_CROSS_BUILD_CC}'" \
	    "g-ir-scanner = '${WRKDIR}/.meson-gi-scanner'" \
	    "g-ir-compiler = '${_EMBER_GI_COMPILER}'" \
	    "pkg-config = ['/usr/bin/env', 'PKG_CONFIG_SYSROOT_DIR=', '${TOOLBASE}/bin/pkg-config']" \
	    '[properties]' \
	    "pkg_config_libdir = ['${TOOLBASE}/lib/pkgconfig', '${TOOLBASE}/share/pkgconfig']" \
	    '[built-in options]' 'pkg_config_path = []' > ${WRKDIR}/.meson-gi-native
.endif

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
.for _input in EMBERBSD_GI_RUBY EMBERBSD_GI_QUERY_CONFIG EMBERBSD_CROSS_BUILD_CC
.if empty(${_input}:M/*) || !empty(${_input}:C/[A-Za-z0-9_.\/-]//g) || !exists(${${_input}})
PKG_FAIL_REASON+= "${_input} must name an existing absolute file without shell metacharacters"
.endif
.endfor
# Cross dependency traversal builds the native tool package independently.
TOOL_DEPENDS+= gobject-introspection>=1.86.0nb4:../../devel/gobject-introspection
EMBERBSD_GI_FILESDIR?= ${.CURDIR}/../../devel/gobject-introspection/files
# Consumers share the launcher and native machine file, but not GI's options.
.if ${EMBERBSD_GI_MESON_OPTIONS:Uyes:tl} == "yes"
MESON_ARGS+= -Dgi_cross_use_prebuilt_gi=true
MESON_ARGS+= -Dgi_cross_ldd_wrapper=${EMBERBSD_GI_FILESDIR}/elf-needed.sh
.endif
MAKE_ENV+= GI_CROSS_LAUNCHER=${EMBERBSD_GI_RUBY:Q}\ ${EMBERBSD_GI_FILESDIR:Q}/target-query.rb
MAKE_ENV+= EMBERBSD_GI_QUERY_CONFIG=${EMBERBSD_GI_QUERY_CONFIG:Q}
MAKE_ENV+= EMBERBSD_GI_TARGET=${_EMBER_GI_TARGET:Q}
MAKE_ENV+= EMBERBSD_GI_READELF=${TOOLDIR:Q}/bin/${_EMBER_GI_TRIPLET}-readelf
MESON_NATIVE_ARGS+= --native-file ${WRKDIR}/.meson-gi-native
MESON_BINARIES+= pkg-config
MESON_BINARY.pkg-config= ${WRKDIR}/.meson-gi-pkg-config

pre-configure: emberbsd-gi-native
.PHONY: emberbsd-gi-native
emberbsd-gi-native:
	${RUN}${SETENV} EMBERBSD_GI_QUERY_CONFIG=${EMBERBSD_GI_QUERY_CONFIG:Q} ${EMBERBSD_GI_RUBY} ${EMBERBSD_GI_FILESDIR}/target-query.rb --check ${WRKDIR} ${CROSS_DESTDIR} ${TOOLDIR}/bin/${_EMBER_GI_TRIPLET}-readelf ${_EMBER_GI_TARGET}
	${RUN}${TEST} -x ${TOOLBASE}/bin/g-ir-scanner && ${TEST} -x ${TOOLBASE}/bin/g-ir-compiler
	${RUN}version=$$(env PKG_CONFIG_SYSROOT_DIR= PKG_CONFIG_PATH= PKG_CONFIG_LIBDIR=${TOOLBASE}/lib/pkgconfig:${TOOLBASE}/share/pkgconfig ${TOOLBASE}/bin/pkg-config --modversion gobject-introspection-1.0); ${TEST} "$$version" = 1.86.0
	${RUN}${SED} \
	    -e 's|@PKG_CONFIG@|${TOOLS_CMD.pkg-config}|g' \
	    -e 's|@GI_SCANNER@|${WRKDIR}/.meson-gi-scanner|g' \
	    -e 's|@GI_COMPILER@|${TOOLBASE}/bin/g-ir-compiler|g' \
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
	    "g-ir-compiler = '${TOOLBASE}/bin/g-ir-compiler'" \
	    "pkg-config = ['/usr/bin/env', 'PKG_CONFIG_SYSROOT_DIR=', '${TOOLBASE}/bin/pkg-config']" \
	    '[properties]' \
	    "pkg_config_libdir = ['${TOOLBASE}/lib/pkgconfig', '${TOOLBASE}/share/pkgconfig']" \
	    '[built-in options]' 'pkg_config_path = []' > ${WRKDIR}/.meson-gi-native
.endif

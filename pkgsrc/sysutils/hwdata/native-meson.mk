# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), genuine host pkg-config inputs for graphics generators.
.if !defined(EMBERBSD_GRAPHICS_NATIVE_MESON_MK)
EMBERBSD_GRAPHICS_NATIVE_MESON_MK=
.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
.if empty(TOOLBASE:M/*) || !empty(TOOLBASE:C/[A-Za-z0-9_.\/-]//g)
PKG_FAIL_REASON+= "Native graphics tool prefix must be absolute without shell metacharacters"
.endif
_EMBERBSD_GRAPHICS_NATIVE= ${WRKDIR}/.meson-graphics-native
# The scanner consumer file already searches this same native TOOLBASE.
# Do not replace its additional, receipt-verified scanner metadata directory.
.if !defined(_EMBERBSD_SCANNER_NATIVE)
MESON_NATIVE_ARGS+= --native-file ${_EMBERBSD_GRAPHICS_NATIVE:Q}
pre-configure: ${_EMBERBSD_GRAPHICS_NATIVE}
.endif
pre-configure: emberbsd-native-graphics-check
.PHONY: emberbsd-native-graphics-check
emberbsd-native-graphics-check:
	${TEST} -x ${TOOLBASE:Q}/bin/pkg-config
.for _pair in ${EMBERBSD_NATIVE_GRAPHICS_PC}
	${RUN} export PKG_CONFIG_PATH= PKG_CONFIG_SYSROOT_DIR=; \
	export PKG_CONFIG_LIBDIR=${TOOLBASE:Q}/lib/pkgconfig:${TOOLBASE:Q}/share/pkgconfig; \
	${TEST} "$$(${TOOLBASE:Q}/bin/pkg-config --modversion ${_pair:C/:.*//:Q})" = ${_pair:C/^[^:]*://:Q} && \
	${TEST} "$$(${TOOLBASE:Q}/bin/pkg-config --variable=prefix ${_pair:C/:.*//:Q})" = ${TOOLBASE:Q} || { \
		echo 'Native graphics metadata does not match the selected host package: ${_pair}' >&2; exit 1; \
	}
.endfor

${_EMBERBSD_GRAPHICS_NATIVE}:
	${RUN}${ECHO} '[binaries]' > ${.TARGET:Q}.tmp
	${RUN}${ECHO} "pkg-config = ['/usr/bin/env', 'PKG_CONFIG_SYSROOT_DIR=', '${TOOLBASE}/bin/pkg-config']" >> ${.TARGET:Q}.tmp
	${RUN}${ECHO} '[properties]' >> ${.TARGET:Q}.tmp
	${RUN}${ECHO} "pkg_config_libdir = ['${TOOLBASE}/lib/pkgconfig', '${TOOLBASE}/share/pkgconfig']" >> ${.TARGET:Q}.tmp
	${RUN}${ECHO} '[built-in options]' >> ${.TARGET:Q}.tmp
	${RUN}${ECHO} 'pkg_config_path = []' >> ${.TARGET:Q}.tmp
	${RUN}${MV} -f ${.TARGET:Q}.tmp ${.TARGET:Q}
.endif
.endif

# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), actual host scanner metadata for consumers.
.if !defined(EMBERBSD_SCANNER_CONSUMER_MK)
EMBERBSD_SCANNER_CONSUMER_MK=
.include "../../devel/wayland/cross-scanner.mk"
.if !empty(EMBERBSD_WAYLAND_SCANNER:C/[A-Za-z0-9_.\/-]//g)
PKG_FAIL_REASON+= "The host scanner prefix must not contain whitespace or shell metacharacters"
.endif
_EMBERBSD_SCANNER_PREFIX= ${EMBERBSD_WAYLAND_SCANNER:H:H}
_EMBERBSD_SCANNER_PC= ${_EMBERBSD_SCANNER_PREFIX}/lib/pkgconfig/wayland-scanner.pc
.if empty(MESON_BINARIES:Mwayland-scanner)
MESON_BINARIES+= wayland-scanner
.endif
.if !defined(MESON_BINARY.wayland-scanner)
MESON_BINARY.wayland-scanner= ${EMBERBSD_WAYLAND_SCANNER}
.elif "${MESON_BINARY.wayland-scanner}" != "${EMBERBSD_WAYLAND_SCANNER}"
PKG_FAIL_REASON+= "The common graphics profile selected a different host Wayland scanner"
.endif
_EMBERBSD_SCANNER_NATIVE= ${WRKDIR}/.meson-scanner-native
MESON_NATIVE_ARGS+= --native-file ${_EMBERBSD_SCANNER_NATIVE:Q}

# Meson's native pkg-config must not inherit pkgsrc's target buildlink search.
# The .pc file is upstream's installed output, never a reconstructed response.
pre-configure: emberbsd-scanner-check ${_EMBERBSD_SCANNER_NATIVE}
.PHONY: emberbsd-scanner-check
emberbsd-scanner-check: emberbsd-wayland-scanner-check
	${TEST} -s ${_EMBERBSD_SCANNER_PC:Q}
	${TEST} -x ${TOOLBASE:Q}/bin/pkg-config
	${RUN} export PKG_CONFIG_PATH= PKG_CONFIG_SYSROOT_DIR=; \
	export PKG_CONFIG_LIBDIR=${_EMBERBSD_SCANNER_PC:H:Q}; \
	${TEST} "$$(${TOOLBASE:Q}/bin/pkg-config --modversion wayland-scanner)" = 1.26.0 && \
	${TEST} "$$(${TOOLBASE:Q}/bin/pkg-config --variable=prefix wayland-scanner)" = ${_EMBERBSD_SCANNER_PREFIX:Q} && \
	${TEST} "$$(${TOOLBASE:Q}/bin/pkg-config --variable=wayland_scanner wayland-scanner)" = ${EMBERBSD_WAYLAND_SCANNER:Q} || { \
		echo 'Wayland scanner native metadata disagrees with the selected executable' >&2; exit 1; \
	}

${_EMBERBSD_SCANNER_NATIVE}:
	${RUN}${ECHO} '[binaries]' > ${.TARGET:Q}.tmp
	${RUN}${ECHO} "pkg-config = ['/usr/bin/env', 'PKG_CONFIG_SYSROOT_DIR=', '${TOOLBASE}/bin/pkg-config']" >> ${.TARGET:Q}.tmp
	${RUN}${ECHO} '[properties]' >> ${.TARGET:Q}.tmp
	${RUN}${ECHO} "pkg_config_libdir = ['${_EMBERBSD_SCANNER_PC:H}', '${TOOLBASE}/lib/pkgconfig', '${TOOLBASE}/share/pkgconfig']" >> ${.TARGET:Q}.tmp
	${RUN}${ECHO} '[built-in options]' >> ${.TARGET:Q}.tmp
	${RUN}${ECHO} 'pkg_config_path = []' >> ${.TARGET:Q}.tmp
	${RUN}${MV} -f ${.TARGET:Q}.tmp ${.TARGET:Q}
.endif

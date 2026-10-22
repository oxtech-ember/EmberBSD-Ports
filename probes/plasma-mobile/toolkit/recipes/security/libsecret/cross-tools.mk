# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), native generators and actual target GTypes.
.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
_EMBERBSD_SECRET_NATIVE_INPUTS= EMBERBSD_VALA_HOST
.if !empty(PKG_OPTIONS:Mdoc)
_EMBERBSD_SECRET_NATIVE_INPUTS+= EMBERBSD_GI_DOCGEN_HOST
.endif
.for _input in ${_EMBERBSD_SECRET_NATIVE_INPUTS}
.if empty(${_input}:M/*) || !empty(${_input}:C/[A-Za-z0-9_.\/-]//g) || !exists(${${_input}}/bin)
PKG_FAIL_REASON+= "${_input} must name an existing absolute native prefix"
.endif
.endfor
BUILD_DEPENDS+= glib2-introspection>=2.90.1nb1:../../devel/glib2-introspection
EMBERBSD_GI_MESON_OPTIONS= no
.include "../../devel/gobject-introspection/cross.mk"
MAKE_ENV+= XDG_DATA_DIRS=${CROSS_DESTDIR:Q}${PREFIX:Q}/share
_EMBERBSD_GI_REAL_SYSROOT!= cd ${CROSS_DESTDIR:Q} && pwd -P
BUILDLINK_TRANSFORM+= I:${_EMBERBSD_GI_REAL_SYSROOT}${PREFIX}:${BUILDLINK_DIR}
MESON_BINARIES+= g-ir-scanner g-ir-compiler gdbus-codegen vapigen vala
MESON_BINARY.g-ir-scanner= ${TOOLBASE}/bin/g-ir-scanner
MESON_BINARY.g-ir-compiler= ${TOOLBASE}/bin/g-ir-compiler
MESON_BINARY.gdbus-codegen= ${TOOLS_CMD.gdbus-codegen}
.if !empty(PKG_OPTIONS:Mdoc)
MESON_BINARIES+= gi-docgen
MESON_BINARY.gi-docgen= ${EMBERBSD_GI_DOCGEN_HOST}/bin/gi-docgen
.endif
MESON_BINARY.vapigen= ${EMBERBSD_VALA_HOST}/bin/vapigen
MESON_BINARY.vala= ${EMBERBSD_VALA_HOST}/bin/valac
MESON_CROSS_VARS+= emberbsd_gi_cross emberbsd_gi_ldd_wrapper
MESON_CROSS.emberbsd_gi_cross= true
MESON_CROSS.emberbsd_gi_ldd_wrapper= '${EMBERBSD_GI_FILESDIR}/elf-needed.sh'
MESON_NATIVE_ARGS+= --native-file ${WRKDIR}/.meson-secret-native
pre-configure: emberbsd-secret-native
.PHONY: emberbsd-secret-native
emberbsd-secret-native:
	${RUN}${TEST} "$$(${EMBERBSD_VALA_HOST}/bin/valac --version)" = 'Vala 0.56.19'
	${RUN}${TEST} "$$(${EMBERBSD_VALA_HOST}/bin/vapigen --version)" = 'Vala API Generator 0.56.19'
	${RUN}${PRINTF} '%s\n' '[binaries]' \
	    "vapigen = '${EMBERBSD_VALA_HOST}/bin/vapigen'" > ${WRKDIR}/.meson-secret-native
.if !empty(PKG_OPTIONS:Mdoc)
	${RUN}${TEST} "$$(${EMBERBSD_GI_DOCGEN_HOST}/bin/gi-docgen --version)" = '2026.1'
	${RUN}${PRINTF} '%s\n' \
	    "gi-docgen = '${EMBERBSD_GI_DOCGEN_HOST}/bin/gi-docgen'" \
	    '[built-in options]' \
	    "pkg_config_path = ['${EMBERBSD_GI_DOCGEN_HOST}/share/pkgconfig']" >> ${WRKDIR}/.meson-secret-native
.endif
.else
TOOL_DEPENDS+= glib2-introspection-[0-9]*:../../devel/glib2-introspection
.if !empty(PKG_OPTIONS:Mdoc)
.include "../../devel/py-gi-docgen/buildlink3.mk"
.endif
.include "../../lang/vala/buildlink3.mk"
.endif

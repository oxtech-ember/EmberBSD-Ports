# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), native generators and actual target GTypes.
.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# Vala and gi-docgen are build-host generators: native packages in TOOLBASE,
# pinned to the versions this recipe was verified with.
TOOL_DEPENDS+= vala>=0.56.19:../../lang/vala
.if !empty(PKG_OPTIONS:Mdoc)
# The Python tool selection sets PYPKGPREFIX for the gi-docgen pattern.
.include "../../lang/python/tool.mk"
TOOL_DEPENDS+= ${PYPKGPREFIX}-gi-docgen>=2026.1:../../devel/py-gi-docgen
.endif
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
MESON_BINARY.gi-docgen= ${TOOLBASE}/bin/gi-docgen
.endif
MESON_BINARY.vapigen= ${TOOLBASE}/bin/vapigen
MESON_BINARY.vala= ${TOOLBASE}/bin/valac
MESON_CROSS_VARS+= emberbsd_gi_cross emberbsd_gi_ldd_wrapper
MESON_CROSS.emberbsd_gi_cross= true
MESON_CROSS.emberbsd_gi_ldd_wrapper= '${EMBERBSD_GI_FILESDIR}/elf-needed.sh'
MESON_NATIVE_ARGS+= --native-file ${WRKDIR}/.meson-secret-native
pre-configure: emberbsd-secret-native
.PHONY: emberbsd-secret-native
emberbsd-secret-native:
	${RUN}v=$$(${TOOLBASE}/bin/valac --version); ${TEST} "$$v" = 'Vala 0.56.19' || \
	    { ${ERROR_MSG} "${TOOLBASE}/bin/valac reports '$$v', this recipe needs 'Vala 0.56.19'"; exit 1; }
	${RUN}v=$$(${TOOLBASE}/bin/vapigen --version); ${TEST} "$$v" = 'Vala API Generator 0.56.19' || \
	    { ${ERROR_MSG} "${TOOLBASE}/bin/vapigen reports '$$v', this recipe needs 'Vala API Generator 0.56.19'"; exit 1; }
	${RUN}${PRINTF} '%s\n' '[binaries]' \
	    "vapigen = '${TOOLBASE}/bin/vapigen'" > ${WRKDIR}/.meson-secret-native
.if !empty(PKG_OPTIONS:Mdoc)
	${RUN}v=$$(${TOOLBASE}/bin/gi-docgen --version); ${TEST} "$$v" = '2026.1' || \
	    { ${ERROR_MSG} "${TOOLBASE}/bin/gi-docgen reports '$$v', this recipe needs '2026.1'"; exit 1; }
	${RUN}${PRINTF} '%s\n' \
	    "gi-docgen = '${TOOLBASE}/bin/gi-docgen'" \
	    '[built-in options]' \
	    "pkg_config_path = ['${TOOLBASE}/share/pkgconfig']" >> ${WRKDIR}/.meson-secret-native
.endif
.else
TOOL_DEPENDS+= glib2-introspection-[0-9]*:../../devel/glib2-introspection
.if !empty(PKG_OPTIONS:Mdoc)
.include "../../devel/py-gi-docgen/buildlink3.mk"
.endif
.include "../../lang/vala/buildlink3.mk"
.endif

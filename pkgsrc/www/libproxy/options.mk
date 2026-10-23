# Origin: EmberBSD (AI-assisted). Runtime proxy backends remain enabled.
PKG_OPTIONS_VAR= PKG_OPTIONS.libproxy
PKG_SUPPORTED_OPTIONS= doc vala
PKG_SUGGESTED_OPTIONS= doc vala
.include "../../mk/bsd.options.mk"
PLIST_VARS+= doc vala
.if !empty(PKG_OPTIONS:Mdoc)
PLIST.doc= yes
MESON_ARGS+= -Ddocs=true
TOOLS_CREATE+= gi-docgen
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && defined(EMBERBSD_GI_DOCGEN_HOST)
.if empty(EMBERBSD_GI_DOCGEN_HOST:M/*) || !exists(${EMBERBSD_GI_DOCGEN_HOST}/bin/gi-docgen)
PKG_FAIL_REASON+= "EMBERBSD_GI_DOCGEN_HOST must name an existing native gi-docgen prefix"
.endif
TOOLS_PATH.gi-docgen= ${EMBERBSD_GI_DOCGEN_HOST}/bin/gi-docgen
MESON_BINARIES+= gi-docgen
MESON_BINARY.gi-docgen= ${TOOLS_PATH.gi-docgen}
pre-configure: emberbsd-proxy-docgen-check
.PHONY: emberbsd-proxy-docgen-check
emberbsd-proxy-docgen-check:
	${RUN}${TEST} "$$(${TOOLS_PATH.gi-docgen} --version)" = '2026.1'
.else
# The Python tool selection sets PYPKGPREFIX for the gi-docgen pattern.
.include "../../lang/python/tool.mk"
TOOL_DEPENDS+= ${PYPKGPREFIX}-gi-docgen>=2026.1:../../devel/py-gi-docgen
TOOLS_PATH.gi-docgen= ${TOOLBASE}/bin/gi-docgen
.endif
.else
MESON_ARGS+= -Ddocs=false
.endif
.if !empty(PKG_OPTIONS:Mvala)
PLIST.vala= yes
MESON_ARGS+= -Dvapi=true
TOOLS_CREATE+= vapigen
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && defined(EMBERBSD_VALA_HOST)
.if empty(EMBERBSD_VALA_HOST:M/*) || !exists(${EMBERBSD_VALA_HOST}/bin/vapigen)
PKG_FAIL_REASON+= "EMBERBSD_VALA_HOST must name an existing native Vala prefix"
.endif
TOOLS_PATH.vapigen= ${EMBERBSD_VALA_HOST}/bin/vapigen
MESON_BINARIES+= vapigen
MESON_BINARY.vapigen= ${TOOLS_PATH.vapigen}
pre-configure: emberbsd-proxy-vapigen-check
.PHONY: emberbsd-proxy-vapigen-check
emberbsd-proxy-vapigen-check:
	${RUN}${TEST} "$$(${TOOLS_PATH.vapigen} --version)" = 'Vala API Generator 0.56.19'
.else
TOOL_DEPENDS+= vala>=0.56.19:../../lang/vala
TOOLS_PATH.vapigen= ${TOOLBASE}/bin/vapigen
.endif
.else
MESON_ARGS+= -Dvapi=false
.endif

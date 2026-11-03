# Origin: EmberBSD (AI-assisted). Runtime proxy backends remain enabled.
PKG_OPTIONS_VAR= PKG_OPTIONS.libproxy
PKG_SUPPORTED_OPTIONS= doc vala tests gnome
PKG_SUGGESTED_OPTIONS= doc vala gnome
.include "../../mk/bsd.options.mk"
PLIST_VARS+= doc vala
.if !empty(PKG_OPTIONS:Mdoc)
PLIST.doc= yes
MESON_ARGS+= -Ddocs=true
TOOLS_CREATE+= gi-docgen
# The Python tool selection sets PYPKGPREFIX for the gi-docgen pattern.
.include "../../lang/python/tool.mk"
TOOL_DEPENDS+= ${PYPKGPREFIX}-gi-docgen>=2026.1:../../devel/py-gi-docgen
TOOLS_PATH.gi-docgen= ${TOOLBASE}/bin/gi-docgen
.else
MESON_ARGS+= -Ddocs=false
.endif
.if !empty(PKG_OPTIONS:Mvala)
PLIST.vala= yes
MESON_ARGS+= -Dvapi=true
TOOLS_CREATE+= vapigen
TOOL_DEPENDS+= vala>=0.56.19:../../lang/vala
TOOLS_PATH.vapigen= ${TOOLBASE}/bin/vapigen
.else
MESON_ARGS+= -Dvapi=false
.endif

.if !empty(PKG_OPTIONS:Mtests)
MESON_ARGS+= -Dtests=true
.else
MESON_ARGS+= -Dtests=false
.endif

.if !empty(PKG_OPTIONS:Mgnome)
MESON_ARGS+= -Dconfig-gnome=true
.include "../../sysutils/gsettings-desktop-schemas/buildlink3.mk"
.else
MESON_ARGS+= -Dconfig-gnome=false
.endif

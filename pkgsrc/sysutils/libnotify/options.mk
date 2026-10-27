# $NetBSD: options.mk,v 1.10 2024/12/01 19:09:42 wiz Exp $

PKG_OPTIONS_VAR=	PKG_OPTIONS.libnotify
PKG_SUPPORTED_OPTIONS=	doc tests
PKG_SUGGESTED_OPTIONS=	# empty
PLIST_VARS+=		doc api_doc

.include "../../mk/bsd.options.mk"

.if !empty(PKG_OPTIONS:Mdoc) || !empty(PKG_OPTIONS:Mtests)
.include "../../lang/python/pyversion.mk"
.endif

.if !empty(PKG_OPTIONS:Mdoc)
TOOL_DEPENDS+=		gtk-doc-[0-9]*:../../textproc/gtk-doc
TOOL_DEPENDS+=		xmlto-[0-9]*:../../textproc/xmlto
.include "../../devel/py-gi-docgen/buildlink3.mk"
PLIST.doc=		yes
.if ${USE_CROSS_COMPILE:Uno:tl} != "yes"
PLIST.api_doc=		yes
.endif
MESON_ARGS+=		-Ddocbook_docs=enabled
MESON_ARGS+=		-Dgtk_doc=true
PRINT_PLIST_AWK+=	/share\/doc\// { $$0 = "$${PLIST.doc}" $$00}
.else
MESON_ARGS+=		-Ddocbook_docs=disabled
MESON_ARGS+=		-Dgtk_doc=false
.endif

.if !empty(PKG_OPTIONS:Mtests)
# Upstream needs these native tools before it creates the C test targets.
TOOL_DEPENDS+=		dbus-[0-9]*:../../sysutils/dbus
TOOL_DEPENDS+=		${PYPKGPREFIX}-dbus-[0-9]*:../../sysutils/py-dbus
MESON_BINARIES+=		python3
MESON_BINARY.python3=	${TOOL_PYTHONBIN}
MESON_ARGS+=		-Dtests=true
BUILDLINK_DEPMETHOD.gtk4=	build
.include "../../x11/gtk4/buildlink3.mk"

pre-configure:
	${TEST} -x ${TOOLBASE}/bin/dbus-run-session || ${FAIL_MSG} "libnotify tests require native dbus-run-session"
	${TOOL_PYTHONBIN} -c 'import dbus; import dbusmock' || ${FAIL_MSG} "libnotify tests require native Python dbus and dbusmock; dbusmock has no packaged provider yet"
.else
MESON_ARGS+=		-Dtests=false
.endif

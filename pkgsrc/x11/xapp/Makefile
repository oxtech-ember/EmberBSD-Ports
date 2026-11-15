# XApp desktop integration library
DISTNAME= xapp-3.4.0
CATEGORIES= x11
MASTER_SITES= ${MASTER_SITE_GITHUB:=linuxmint/}
GITHUB_TAG= ${PKGVERSION_NOREV}
HOMEPAGE= https://github.com/linuxmint/xapp
COMMENT= Cross-desktop application libraries and resources
LICENSE= gnu-lgpl-v3
USE_TOOLS+= pkg-config msgfmt xgettext gdbus-codegen
MESON_BINARIES+= gdbus-codegen
MESON_BINARY.gdbus-codegen= ${TOOLS_CMD.gdbus-codegen}
USE_PKGLOCALEDIR= yes
REPLACE_TOOL_PYTHON+= schemas/meson_install_schemas.py
GLIB_SCHEMAS+= org.x.apps.gschema.xml
DEPENDS+= ${PYPKGPREFIX}-gobject3-[0-9]*:../../devel/py-gobject3
DEPENDS+= xapp-symbolic-icons>=1.1.2:../../graphics/xapp-symbolic-icons
MESON_ARGS+= -Dintrospection=true -Dpy-overrides-dir=${PREFIX}/${PYSITELIB}/gi/overrides
# The shared application library and GI only; do not install Mint services.
MESON_ARGS+= -Dapp-lib-only=true -Dstatus-notifier=false -Dkbd-layout-controller=disabled
MESON_ARGS+= -Dmate=false -Dxfce=false -Dgtk-layer-shell=disabled -Ddocs=false -Dvapi=false
.include "../../lang/python/application.mk"
.include "../../x11/libX11/buildlink3.mk"
.include "../../sysutils/dbus/buildlink3.mk"
.include "../../devel/py-gobject3-common/buildlink3.mk"

.include "../../devel/glib2/buildlink3.mk"
.include "../../x11/gtk3/buildlink3.mk"
# Match the selected GTK provider. XApp always compiles its X11 backend and
# generates GI against Gtk-3.0; do not silently lose an enabled Wayland path.
.if empty(PKG_BUILD_OPTIONS.gtk3:Mx11) || empty(PKG_BUILD_OPTIONS.gtk3:Mintrospection)
PKG_FAIL_REASON+= "XApp requires GTK3 built with x11 and introspection"
.endif
.if !empty(PKG_BUILD_OPTIONS.gtk3:Mwayland)
MESON_ARGS+= -Dwayland-backend=enabled
TOOL_DEPENDS+= wayland>=1.26.0:../../devel/wayland
.include "../../devel/wayland/buildlink3.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
.include "../../devel/wayland-protocols/cross-scanner.mk"
.endif
.else
MESON_ARGS+= -Dwayland-backend=disabled
.endif
.include "../../graphics/cairo/buildlink3.mk"
.include "../../devel/gobject-introspection/buildlink3.mk"
BUILD_DEPENDS+= glib2-introspection-[0-9]*:../../devel/glib2-introspection
EMBERBSD_GI_MESON_OPTIONS= no
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
MAKE_ENV+= XDG_DATA_DIRS=${CROSS_DESTDIR:Q}${PREFIX:Q}/share
MESON_BINARIES+= g-ir-scanner g-ir-compiler
MESON_BINARY.g-ir-scanner= ${TOOLBASE}/bin/g-ir-scanner
MESON_BINARY.g-ir-compiler= ${TOOLBASE}/bin/g-ir-compiler
MESON_CROSS_VARS+= emberbsd_gi_cross emberbsd_gi_ldd_wrapper
MESON_CROSS.emberbsd_gi_cross= true
MESON_CROSS.emberbsd_gi_ldd_wrapper= '${EMBERBSD_GI_FILESDIR}/elf-needed.sh'
.endif
.include "../../devel/gobject-introspection/cross.mk"
.include "../../devel/glib2/schemas.mk"
.include "../../devel/meson/build.mk"
.include "../../mk/bsd.pkg.mk"

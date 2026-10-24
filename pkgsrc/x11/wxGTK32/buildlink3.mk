# $NetBSD: buildlink3.mk,v 1.19 2026/09/02 19:05:34 wiz Exp $

BUILDLINK_TREE+=	wxGTK32

.if !defined(WXGTK32_BUILDLINK3_MK)
WXGTK32_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.wxGTK32+=	wxGTK32>=3.2
BUILDLINK_ABI_DEPENDS.wxGTK32+=	wxGTK32>=3.2.12
BUILDLINK_PKGSRCDIR.wxGTK32?=	../../x11/wxGTK32

BUILDLINK_INCDIRS.wxGTK32+=	include/wx-3.2
PREPEND_PATH+=			${PREFIX}/libexec/wx-3.2
CONFIGURE_ARGS+=		--with-wx-version=3.2
CONFIGURE_ARGS+=		--with-wx-config=${PREFIX}/libexec/wx-3.2/wx-config

pkgbase := wxGTK32
.include "../../mk/pkg-build-options.mk"

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD" && empty(PKG_BUILD_OPTIONS.wxGTK32:Mcmake)
# AI-assisted: read the target POSIX script on the build host.
# The installed libexec entry has an absolute target-prefix symlink.
_WXGTK32_CROSS_CONFIG=	${CROSS_DESTDIR}${BUILDLINK_PREFIX.wxGTK32}/lib/wx/config/${MACHINE_GNU_PLATFORM}-gtk3-unicode-3.2
CMAKE_CONFIGURE_ARGS+=	-DwxWidgets_CONFIG_EXECUTABLE:FILEPATH=${_WXGTK32_CROSS_CONFIG}
CMAKE_CONFIGURE_ARGS+=	-DwxWidgets_CONFIG_OPTIONS:STRING=--prefix=${BUILDLINK_DIR}\;--exec-prefix=${BUILDLINK_DIR}
.endif

.include "../../devel/gettext-lib/buildlink3.mk"
.include "../../devel/zlib/buildlink3.mk"
.include "../../mk/jpeg.buildlink3.mk"
.include "../../graphics/png/buildlink3.mk"
.include "../../graphics/tiff/buildlink3.mk"
.if ${OPSYS} != "Darwin"
.include "../../x11/gtk3/buildlink3.mk"
.endif
.endif # WXGTK32_BUILDLINK3_MK

BUILDLINK_TREE+=	-wxGTK32

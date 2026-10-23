# $NetBSD: buildlink3.mk,v 1.1 2025/07/27 09:18:49 wiz Exp $
# Adapted from x11/tk90. Local changes are AI-assisted.

BUILDLINK_TREE+=	tk
.if !defined(TK_BUILDLINK3_MK)
TK_BUILDLINK3_MK:=
.include "../../x11/tk/Makefile.version"
BUILDLINK_API_DEPENDS.tk+=	tk>=${TK_VERSION}
BUILDLINK_ABI_DEPENDS.tk+=	tk>=${TK_VERSION}
BUILDLINK_PKGSRCDIR.tk?=	../../x11/tk
BUILDLINK_FILES.tk+=	bin/wish*
BUILDLINK_TRANSFORM+=	l:tk:tcl9tk${TK_BASEVER}
TKCONFIG_SH?=	${BUILDLINK_PREFIX.tk}/lib/tkConfig.sh
_TOOLS_USE_PKGSRC.wish=	yes
WISH=	${BUILDLINK_PREFIX.tk}/bin/wish

pkgbase := tk
.include "../../mk/pkg-build-options.mk"
.if ${PKG_BUILD_OPTIONS.tk:Mxft2}
.  include "../../x11/libXft/buildlink3.mk"
.endif
.if ${PKG_BUILD_OPTIONS.tk:Mbidi}
.  include "../../fonts/harfbuzz/buildlink3.mk"
.endif
.if ${PKG_BUILD_OPTIONS.tk:Mcups}
.  include "../../print/libcups/buildlink3.mk"
.endif
.if ${PKG_BUILD_OPTIONS.tk:Matk}
.  include "../../devel/at-spi2-core/buildlink3.mk"
.endif
.if empty(PKG_BUILD_OPTIONS.tk:Maqua)
.  include "../../x11/libX11/buildlink3.mk"
.  include "../../x11/libXext/buildlink3.mk"
.  include "../../x11/libXScrnSaver/buildlink3.mk"
.endif
.include "../../lang/tcl/buildlink3.mk"
.include "../../mk/pthread.buildlink3.mk"
.endif
BUILDLINK_TREE+=	-tk

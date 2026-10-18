# $NetBSD$
BUILDLINK_TREE+=	occt
.if !defined(OCCT_BUILDLINK3_MK)
OCCT_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.occt+=	occt>=8.0.1
BUILDLINK_ABI_DEPENDS.occt?=	occt>=8.0.1
BUILDLINK_PKGSRCDIR.occt?=	../../cad/occt
BUILDLINK_INCDIRS.occt+=		include/opencascade
CMAKE_CONFIGURE_ARGS+=	-DOCC_INCLUDE_DIR=${BUILDLINK_PREFIX.occt}/include/opencascade
pkgbase := occt
.include "../../mk/pkg-build-options.mk"
.if !empty(PKG_BUILD_OPTIONS.occt:Mx11)
.include "../../graphics/MesaLib/buildlink3.mk"
.include "../../x11/libX11/buildlink3.mk"
.endif
.if !empty(PKG_BUILD_OPTIONS.occt:Mocct-draw)
.include "../../lang/tcl/buildlink3.mk"
.include "../../x11/tk/buildlink3.mk"
.endif
.include "../../fonts/fontconfig/buildlink3.mk"
.include "../../graphics/freetype2/buildlink3.mk"
BUILDLINK_API_DEPENDS.freeimage+=	freeimage>=3.19.25nb3
.include "../../graphics/freeimage/buildlink3.mk"
BUILDLINK_API_DEPENDS.eigen3+=	eigen3>=5.0.1
.include "../../math/eigen3/buildlink3.mk"
.include "../../textproc/rapidjson/buildlink3.mk"
.endif
BUILDLINK_TREE+=	-occt

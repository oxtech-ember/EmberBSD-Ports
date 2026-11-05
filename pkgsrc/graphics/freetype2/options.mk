# $NetBSD: options.mk,v 1.6 2023/11/09 20:10:32 nia Exp $

PKG_OPTIONS_VAR=	PKG_OPTIONS.freetype2
PKG_SUPPORTED_OPTIONS=	brotli png subpixel
PKG_SUGGESTED_OPTIONS=	brotli png subpixel

.include "../../mk/bsd.options.mk"

# Support decompression of WOFF2 streams.
.if !empty(PKG_OPTIONS:Mbrotli)
CONFIGURE_ARGS+=	--with-brotli=yes
.include "../../archivers/brotli/buildlink3.mk"
.else
CONFIGURE_ARGS+=	--with-brotli=no
.endif

# Support bitmaps in OpenType fonts.
.if !empty(PKG_OPTIONS:Mpng)
CONFIGURE_ARGS+=	--with-png=yes
.include "../../graphics/png/buildlink3.mk"
.else
CONFIGURE_ARGS+=	--with-png=no
.endif

# Enable the higher-resolution LCD renderer, with filtering selected by users.
.if !empty(PKG_OPTIONS:Msubpixel)
SUBST_CLASSES+=		subpixel
SUBST_STAGE.subpixel=	post-extract
SUBST_FILES.subpixel=	include/freetype/config/ftoption.h
SUBST_SED.subpixel=	-e 's@/\* \#define FT_CONFIG_OPTION_SUBPIXEL_RENDERING \*/@\#define FT_CONFIG_OPTION_SUBPIXEL_RENDERING@'
.endif

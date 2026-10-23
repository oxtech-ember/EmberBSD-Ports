# $NetBSD: buildlink3.mk,v 1.2 2026/08/12 12:39:42 adam Exp $

BUILDLINK_TREE+=	ffmpeg9

.if !defined(FFMPEG9_BUILDLINK3_MK)
FFMPEG9_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.ffmpeg9+=	ffmpeg9>=9.0.2
BUILDLINK_ABI_DEPENDS.ffmpeg9?=	ffmpeg9>=9.0.2
BUILDLINK_PKGSRCDIR.ffmpeg9?=	../../multimedia/ffmpeg9

pkgbase := ffmpeg9
.include "../../mk/pkg-build-options.mk"

.include "../../mk/bsd.fast.prefs.mk"

.if !empty(PKG_BUILD_OPTIONS.ffmpeg9:Mass)
.  include "../../multimedia/libass/buildlink3.mk"
.endif

.if !empty(PKG_BUILD_OPTIONS.ffmpeg9:Maom)
.  include "../../multimedia/libaom/buildlink3.mk"
.endif

.if !empty(PKG_BUILD_OPTIONS.ffmpeg9:Mbluray)
.  include "../../multimedia/libbluray/buildlink3.mk"
.endif

.if !empty(PKG_BUILD_OPTIONS.ffmpeg9:Mfdk-aac)
.  include "../../audio/fdk-aac/buildlink3.mk"
.endif

.if !empty(PKG_BUILD_OPTIONS.ffmpeg9:Mfontconfig)
.  include "../../fonts/fontconfig/buildlink3.mk"
.endif

.if !empty(PKG_BUILD_OPTIONS.ffmpeg9:Mfreetype)
.  include "../../graphics/freetype2/buildlink3.mk"
.  include "../../fonts/harfbuzz/buildlink3.mk"
.endif

.if !empty(PKG_BUILD_OPTIONS.ffmpeg9:Mgnutls)
.  include "../../security/gnutls/buildlink3.mk"
.endif

.if !empty(PKG_BUILD_OPTIONS.ffmpeg9:Mjack)
.  include "../../audio/jack/buildlink3.mk"
.endif

.if !empty(PKG_BUILD_OPTIONS.ffmpeg9:Mlame)
.  include "../../audio/lame/buildlink3.mk"
.endif

.if !empty(PKG_BUILD_OPTIONS.ffmpeg9:Mlibvpx)
.  include "../../multimedia/libvpx/buildlink3.mk"
.endif

.if !empty(PKG_BUILD_OPTIONS.ffmpeg9:Mlibwebp)
.  include "../../graphics/libwebp/buildlink3.mk"
.endif

.if !empty(PKG_BUILD_OPTIONS.ffmpeg9:Mmbedtls)
.  include "../../security/mbedtls/buildlink3.mk"
.endif

.if !empty(PKG_BUILD_OPTIONS.ffmpeg9:Mopencore-amr)
.  include "../../audio/opencore-amr/buildlink3.mk"
.endif

.if !empty(PKG_BUILD_OPTIONS.ffmpeg9:Mopenssl)
.  include "../../security/openssl/buildlink3.mk"
.endif

.if !empty(PKG_BUILD_OPTIONS.ffmpeg9:Mopus)
.  include "../../audio/libopus/buildlink3.mk"
.endif

.if !empty(PKG_BUILD_OPTIONS.ffmpeg9:Mpulseaudio)
.  include "../../audio/pulseaudio/buildlink3.mk"
.endif

.if !empty(PKG_BUILD_OPTIONS.ffmpeg9:Mrav1e)
.  include "../../multimedia/rav1e/buildlink3.mk"
.endif

.if !empty(PKG_BUILD_OPTIONS.ffmpeg9:Mrpi)
.  include "../../misc/raspberrypi-userland/buildlink3.mk"
.endif

.if !empty(PKG_BUILD_OPTIONS.ffmpeg9:Mrtmp)
.  include "../../net/rtmpdump/buildlink3.mk"
.endif

.if !empty(PKG_BUILD_OPTIONS.ffmpeg9:Mspeex)
.  include "../../audio/speex/buildlink3.mk"
.endif

.if !empty(PKG_BUILD_OPTIONS.ffmpeg9:Mtesseract)
.  include "../../graphics/tesseract/buildlink3.mk"
.endif

.if !empty(PKG_BUILD_OPTIONS.ffmpeg9:Mtheora)
.  include "../../multimedia/libtheora/buildlink3.mk"
.endif

.if !empty(PKG_BUILD_OPTIONS.ffmpeg9:Mvorbis)
.  include "../../audio/libvorbis/buildlink3.mk"
.endif

.if !empty(PKG_BUILD_OPTIONS.ffmpeg9:Mx11)
.  include "../../x11/libxcb/buildlink3.mk"
.endif

.if !empty(PKG_BUILD_OPTIONS.ffmpeg9:Mx264)
.  include "../../multimedia/x264/buildlink3.mk"
.endif

.if !empty(PKG_BUILD_OPTIONS.ffmpeg9:Mx265)
.  include "../../multimedia/x265/buildlink3.mk"
.endif

.if !empty(PKG_BUILD_OPTIONS.ffmpeg9:Mxvid)
.  include "../../multimedia/xvidcore/buildlink3.mk"
.endif

.if !empty(PKG_BUILD_OPTIONS.ffmpeg9:Maom) || !empty(PKG_BUILD_OPTIONS.ffmpeg9:Mrav1e)
.  include "../../multimedia/dav1d/buildlink3.mk"
.endif

.if !empty(PKG_BUILD_OPTIONS.ffmpeg9:Mvaapi) && !empty(PKG_BUILD_OPTIONS.ffmpeg9:Mx11)
.  include "../../multimedia/libva/buildlink3.mk"
.endif

.if !empty(PKG_BUILD_OPTIONS.ffmpeg9:Mvdpau) && !empty(PKG_BUILD_OPTIONS.ffmpeg9:Mx11)
.  include "../../multimedia/libvdpau/buildlink3.mk"
.endif

BUILDLINK_INCDIRS.ffmpeg9+=		include/ffmpeg9
BUILDLINK_LIBDIRS.ffmpeg9+=		lib/ffmpeg9
BUILDLINK_FNAME_TRANSFORM.ffmpeg9+=	-e 's|lib/ffmpeg9/pkgconfig/|lib/pkgconfig/|'

.include "../../archivers/bzip2/buildlink3.mk"
.include "../../archivers/xz/buildlink3.mk"
.include "../../devel/libgetopt/buildlink3.mk"
.include "../../devel/zlib/buildlink3.mk"
.include "../../textproc/libxml2/buildlink3.mk"
.endif # FFMPEG9_BUILDLINK3_MK

BUILDLINK_TREE+=	-ffmpeg9

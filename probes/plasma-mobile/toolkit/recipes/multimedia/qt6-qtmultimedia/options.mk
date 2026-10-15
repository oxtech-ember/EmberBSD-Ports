# $NetBSD: options.mk,v 1.8 2026/01/28 17:10:52 adam Exp $

PKG_OPTIONS_VAR=	PKG_OPTIONS.qt6-qtmultimedia
PKG_SUPPORTED_OPTIONS=	gstreamer pulseaudio

.include "../../mk/bsd.fast.prefs.mk"

PLIST_VARS+=		dmabuf ffmpeg gstreamer pulseaudio vaapi x11

.if ${OPSYS} != "Darwin"
# The common EGL provider exposes the DMA-BUF import declarations.
PLIST.dmabuf=		yes
PKG_SUGGESTED_OPTIONS+=	gstreamer pulseaudio
.endif

.include "../../mk/bsd.options.mk"

.if !empty(PKG_OPTIONS:Mgstreamer)
CONFIGURE_ARGS+=	-gstreamer
.include "../../multimedia/gst-plugins1-base/buildlink3.mk"
.include "../../multimedia/gst-plugins1-bad/buildlink3.mk"
PLIST.gstreamer=	yes
.else
CONFIGURE_ARGS+=	-no-gstreamer
.endif

# the pulseaudio option must come after the gstreamer option
.if !empty(PKG_OPTIONS:Mpulseaudio)
CONFIGURE_ARGS+=	-pulseaudio
PLIST.pulseaudio=	yes
.include "../../audio/pulseaudio/buildlink3.mk"
.else
CONFIGURE_ARGS+=	-no-pulseaudio
.endif

# NetBSD supports FFmpeg video without a low-level audio backend.
# Keep the normal PulseAudio and Darwin selection on other platforms.
.if !empty(PKG_OPTIONS:Mpulseaudio) || ${OPSYS} == "Darwin" || ${OPSYS} == "NetBSD"
CONFIGURE_ARGS+=	-ffmpeg
.include "../../multimedia/ffmpeg9/buildlink3.mk"
PLIST.ffmpeg=		yes
.  if ${PKG_BUILD_OPTIONS.ffmpeg9:Mvaapi}
PLIST.vaapi=		yes
.  endif
.  if ${OPSYS} != "Darwin"
PLIST.x11=			yes
.  endif
.endif

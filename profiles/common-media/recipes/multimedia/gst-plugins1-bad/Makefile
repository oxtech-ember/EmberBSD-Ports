# $NetBSD: Makefile,v 1.29 2026/09/02 19:03:41 wiz Exp $

PKGNAME=	${DISTNAME:S/plugins/plugins1/}
PKGREVISION=	1
CATEGORIES=	multimedia gnome

COMMENT=	Open source multimedia framework - bad plugins

TOOL_DEPENDS+=	glib2-introspection-[0-9]*:../../devel/glib2-introspection

USE_TOOLS+=	xgettext

GST_PLUGINS+=	accurip
GST_PLUGINS+=	adpcmdec
GST_PLUGINS+=	adpcmenc
GST_PLUGINS+=	aiff
GST_PLUGINS+=	asfmux
GST_PLUGINS+=	audiobuffersplit
GST_PLUGINS+=	audiofxbad
GST_PLUGINS+=	audiolatency
GST_PLUGINS+=	audiomixmatrix
GST_PLUGINS+=	audiovisualizers
GST_PLUGINS+=	autoconvert
GST_PLUGINS+=	bayer
GST_PLUGINS+=	camerabin2
GST_PLUGINS+=	coloreffects
GST_PLUGINS+=	debugutils
GST_PLUGINS+=	dvbsubenc
GST_PLUGINS+=	dvbsuboverlay
GST_PLUGINS+=	dvdspu
GST_PLUGINS+=	faceoverlay
GST_PLUGINS+=	festival
GST_PLUGINS+=	fieldanalysis
GST_PLUGINS+=	freeverb
GST_PLUGINS+=	frei0r
GST_PLUGINS+=	gaudieffects
GST_PLUGINS+=	gdp
GST_PLUGINS+=	geometrictransform
GST_PLUGINS+=	id3tag
GST_PLUGINS+=	inter
GST_PLUGINS+=	interlace
GST_PLUGINS+=	ivfparse
GST_PLUGINS+=	ivtc
GST_PLUGINS+=	jp2kdecimator
GST_PLUGINS+=	jpegformat
GST_PLUGINS+=	librfb
GST_PLUGINS+=	midi
GST_PLUGINS+=	mpegdemux
GST_PLUGINS+=	mpegpsmux
GST_PLUGINS+=	mpegtsdemux
GST_PLUGINS+=	mpegtsmux
GST_PLUGINS+=	mxf
GST_PLUGINS+=	netsim
GST_PLUGINS+=	onvif
GST_PLUGINS+=	pcapparse
GST_PLUGINS+=	pnm
GST_PLUGINS+=	proxy
GST_PLUGINS+=	rawparse
GST_PLUGINS+=	removesilence
GST_PLUGINS+=	rist
GST_PLUGINS+=	rtmp2
GST_PLUGINS+=	rtp
GST_PLUGINS+=	sdp
GST_PLUGINS+=	segmentclip
GST_PLUGINS+=	siren
GST_PLUGINS+=	smooth
GST_PLUGINS+=	speed
GST_PLUGINS+=	subenc
GST_PLUGINS+=	switchbin
GST_PLUGINS+=	timecode
# XXX: maybe revisit
# XXX: multimedia/gst-plugins1-transcode
GST_PLUGINS+=	transcode
GST_PLUGINS+=	videofilters
GST_PLUGINS+=	videoframe_audiolevel
GST_PLUGINS+=	videoparsers
GST_PLUGINS+=	videosignal
GST_PLUGINS+=	vmnc

GST_PLUGINS+=	introspection
GST_PLUGINS+=	nls

LDFLAGS.SunOS+=	-lsocket -lnsl

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# Host generators, target GType queries; preserve all GIR and typelib outputs.
TOOL_DEPENDS+= glib2-tools>=2.90.1:../../devel/glib2-tools
EMBERBSD_GI_MESON_OPTIONS= no
.include "../../devel/gobject-introspection/cross.mk"
MESON_ARGS+= -Dintrospection=enabled
MESON_BINARIES+= glib-mkenums glib-genmarshal g-ir-scanner g-ir-compiler
MESON_BINARY.glib-mkenums= ${TOOLBASE}/bin/glib-mkenums
MESON_BINARY.glib-genmarshal= ${TOOLBASE}/bin/glib-genmarshal
MESON_BINARY.g-ir-scanner= ${TOOLBASE}/bin/g-ir-scanner
MESON_BINARY.g-ir-compiler= ${TOOLBASE}/bin/g-ir-compiler
MESON_CROSS_VARS+= emberbsd_gi_cross emberbsd_gi_ldd_wrapper
MESON_CROSS.emberbsd_gi_cross= true
MESON_CROSS.emberbsd_gi_ldd_wrapper= '${EMBERBSD_GI_FILESDIR}/elf-needed.sh'
.endif

.include "Makefile.common"
BUILDLINK_DEPMETHOD.gobject-introspection=	build
.include "../../devel/gobject-introspection/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

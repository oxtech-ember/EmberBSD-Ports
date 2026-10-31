# $NetBSD$
# Origin: EmberBSD (AI-assisted), first port for the KWin screencast plugin.

DISTNAME=	pipewire-1.6.10
CATEGORIES=	multimedia
MASTER_SITES=	https://gitlab.freedesktop.org/pipewire/pipewire/-/archive/${PKGVERSION_NOREV}/

HOMEPAGE=	https://pipewire.org/
COMMENT=	Server and user-space API to handle multimedia pipelines
LICENSE=	mit AND gnu-lgpl-v2.1

USE_TOOLS+=	pkg-config
PYTHON_FOR_BUILD_ONLY=	tool

# NetBSD headers hide pthread_t, CLOCK_MONOTONIC and alloca without the
# default feature set; spa headers include <stdlib.h> first.
CFLAGS.NetBSD+=	-D_NETBSD_SOURCE

MESON_ARGS+=	-Dexamples=disabled
MESON_ARGS+=	-Dtests=disabled
MESON_ARGS+=	-Dinstalled_tests=disabled
MESON_ARGS+=	-Dgstreamer=disabled
MESON_ARGS+=	-Dgstreamer-device-provider=disabled
MESON_ARGS+=	-Dlibsystemd=disabled
MESON_ARGS+=	-Dsystemd-system-service=disabled
MESON_ARGS+=	-Dsystemd-user-service=disabled
MESON_ARGS+=	-Dalsa=disabled
MESON_ARGS+=	-Dpipewire-alsa=disabled
MESON_ARGS+=	-Djack=disabled
MESON_ARGS+=	-Dpipewire-jack=disabled
MESON_ARGS+=	-Dbluez5=disabled
MESON_ARGS+=	-Dlibcamera=disabled
MESON_ARGS+=	-Droc=disabled
MESON_ARGS+=	-Dvulkan=disabled
MESON_ARGS+=	-Davahi=disabled
MESON_ARGS+=	-Dsdl2=disabled
# The V4L2 LD_PRELOAD shim needs <linux/videodev2.h> and the Linux
# off64_t/O_TMPFILE/O_LARGEFILE file API.
MESON_ARGS+=	-Dpipewire-v4l2=disabled
MESON_ARGS+=	-Dbluez5-codec-aptx=disabled
MESON_ARGS+=	-Dsession-managers=

# PipeWire probes a native C compiler; provide the host compiler through
# a meson native file.
pre-configure: pipewire-native-file
.PHONY: pipewire-native-file
pipewire-native-file:
	${PRINTF} '%s\n' '[binaries]' "c = '/usr/bin/cc'" \
	    '[built-in options]' > ${WRKDIR}/.meson-pipewire-native
MESON_NATIVE_ARGS+=	--native-file ${WRKDIR}/.meson-pipewire-native

# The modules have install_rpath ${PREFIX}/lib/pipewire-0.3. The wrappers drop
# meson's build-tree rpath, so meson's install-time rewrite has no room for the
# longer rpath unless the directory is already in the link-time rpath.
LDFLAGS+=	${COMPILER_RPATH_FLAG}${PREFIX}/lib/pipewire-0.3

.include "../../devel/meson/build.mk"
.if ${OPSYS} == "NetBSD"
# epoll and signalfd for spa/plugins/support/system.c, as on FreeBSD.
.  include "../../devel/libepoll-shim/buildlink3.mk"
CPPFLAGS+=	-I${BUILDLINK_PREFIX.libepoll-shim}/include/libepoll-shim
.endif
.include "../../devel/glib2/buildlink3.mk"
.include "../../sysutils/dbus/buildlink3.mk"
.include "../../devel/libudev-bsd/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

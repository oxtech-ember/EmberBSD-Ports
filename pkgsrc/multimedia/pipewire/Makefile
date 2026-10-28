# $NetBSD$
# Origin: EmberBSD (AI-assisted), first port for the KWin screencast plugin.

DISTNAME=	pipewire-1.6.9
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

.include "../../devel/meson/build.mk"
.include "../../devel/glib2/buildlink3.mk"
.include "../../sysutils/dbus/buildlink3.mk"
.include "../../devel/libudev-bsd/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

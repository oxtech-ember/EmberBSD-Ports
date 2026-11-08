# $NetBSD$

DISTNAME=	callaudiod-0.1.10
CATEGORIES=	audio
MASTER_SITES=	https://gitlab.com/mobian1/callaudiod/-/archive/${PKGVERSION_NOREV}/
EXTRACT_SUFX=	.tar.gz

HOMEPAGE=	https://gitlab.com/mobian1/callaudiod
COMMENT=	D-Bus client library for call audio routing
LICENSE=	gnu-gpl-v3 AND gnu-lgpl-v3

USE_TOOLS+=	pkg-config

# The daemon requires ALSA and is not built. The library is a D-Bus client.
MESON_ARGS+=	-Ddaemon=false
MESON_ARGS+=	-Dgtk_doc=false

# GLib's code generators are build-machine programs. The cross environment's
# sysroot prefix would otherwise be added to those host paths, so Meson
# rejects them. This wrapper is only the native pkg-config.
MESON_NATIVE_EXTRA_ARGS+=	--native-file ${WRKDIR}/.meson-callaudio-native
pre-configure: callaudio-native-pkgconfig
.PHONY: callaudio-native-pkgconfig
callaudio-native-pkgconfig:
	${RUN}${MKDIR} ${WRKDIR}
	${RUN}${PRINTF} '%s\n' '#!/bin/sh' 'unset PKG_CONFIG_SYSROOT_DIR' \
	    'exec ${TOOLS_PATH.pkg-config} "$$@"' > ${WRKDIR}/callaudio-pkg-config
	${RUN}${CHMOD} 755 ${WRKDIR}/callaudio-pkg-config
	${RUN}${PRINTF} '%s\n' '[binaries]' \
	    "pkg-config = '${WRKDIR}/callaudio-pkg-config'" \
	    > ${WRKDIR}/.meson-callaudio-native

.include "../../devel/meson/build.mk"
.include "../../devel/glib2/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

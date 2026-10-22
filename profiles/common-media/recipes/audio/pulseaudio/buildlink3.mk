# $NetBSD: buildlink3.mk,v 1.50 2026/09/02 19:00:58 wiz Exp $

BUILDLINK_TREE+=	pulseaudio

.if !defined(PULSEAUDIO_BUILDLINK3_MK)
PULSEAUDIO_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.pulseaudio+=	pulseaudio>=16.1
BUILDLINK_ABI_DEPENDS.pulseaudio+=	pulseaudio>=17.0nb6
BUILDLINK_PKGSRCDIR.pulseaudio?=	../../audio/pulseaudio

.include "../../mk/bsd.fast.prefs.mk"

# Consumers use the same target-sysroot check as the package recipe.
.if ${OPSYS} != "NetBSD" || !exists(${_CROSS_DESTDIR}/usr/include/sys/atomic.h)
.include "../../devel/libatomic_ops/buildlink3.mk"
.endif

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# libpulse needs libpulsecommon from lib/pulseaudio through its RPATH.
# The cross GNU ld has no sysroot, so it finds it only through rpath-link.
LDFLAGS+=	-Wl,-rpath-link,${CROSS_DESTDIR}${LOCALBASE}/lib/pulseaudio
.endif

BUILDLINK_LIBDIRS.pulseaudio+=		lib/pulseaudio
BUILDLINK_RPATHDIRS.pulseaudio+=	lib/pulseaudio

_WRAP_EXTRA_ARGS.LIBTOOL+=	-L${PREFIX}/lib/pulseaudio

pkgbase:= pulseaudio
.include "../../mk/pkg-build-options.mk"

.include "../../mk/bsd.fast.prefs.mk"

.if ${PKG_BUILD_OPTIONS.pulseaudio:Mx11}
.include "../../x11/libICE/buildlink3.mk"
.include "../../x11/libSM/buildlink3.mk"
.include "../../x11/libX11/buildlink3.mk"
.include "../../x11/libXtst/buildlink3.mk"
.endif

.include "../../audio/libsndfile/buildlink3.mk"
.include "../../devel/glib2/buildlink3.mk"
.include "../../sysutils/dbus/buildlink3.mk"
.endif # PULSEAUDIO_BUILDLINK3_MK

BUILDLINK_TREE+=	-pulseaudio

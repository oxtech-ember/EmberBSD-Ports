# $NetBSD: Makefile,v 1.64 2026/06/01 13:31:40 wiz Exp $

# Origin: EmberBSD (AI-assisted). Keymap compilation reads these data at runtime.
BUILDLINK_DEPMETHOD.xkeyboard-config= full
.include "Makefile.common"

PKGREVISION= 2

MESON_ARGS+=	-Denable-docs=false

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD" && \
    (${MACHINE_ARCH} == "aarch64" || ${MACHINE_ARCH} == "x86_64")
PKGREVISION=	3	# Record the base libc SONAME.
.endif

.include "../../mk/bsd.pkg.mk"

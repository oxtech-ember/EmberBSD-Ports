# $NetBSD: Makefile,v 1.64 2026/06/01 13:31:40 wiz Exp $

# Origin: EmberBSD (AI-assisted). Keymap compilation reads these data at runtime.
BUILDLINK_DEPMETHOD.xkeyboard-config= full
.include "Makefile.common"

PKGREVISION= 2

MESON_ARGS+=	-Denable-docs=false

.include "../../mk/bsd.pkg.mk"

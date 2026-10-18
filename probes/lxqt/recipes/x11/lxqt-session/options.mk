# $NetBSD: options.mk,v 1.2 2024/08/25 06:19:20 wiz Exp $

PKG_OPTIONS_VAR=		PKG_OPTIONS.lxqt-session
PKG_SUPPORTED_OPTIONS=		udev

# Preserve the upstream monitor with the common BSD libudev implementation.
.if ${OPSYS} == "NetBSD"
PKG_SUGGESTED_OPTIONS+=	udev
.endif

.include "../../mk/bsd.options.mk"

.if !empty(PKG_OPTIONS:Mudev)
.  if ${OPSYS} == "NetBSD"
.    include "../../devel/libudev-bsd/buildlink3.mk"
.  else
.    include "../../sysutils/libudev/buildlink3.mk"
.  endif
.else
CMAKE_CONFIGURE_ARGS+=	-DWITH_LIBUDEV=OFF
.endif

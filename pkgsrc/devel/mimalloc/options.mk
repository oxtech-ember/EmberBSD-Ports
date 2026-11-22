# $NetBSD$

PKG_OPTIONS_VAR=		PKG_OPTIONS.mimalloc
PKG_SUPPORTED_OPTIONS=	malloc-override dynamic-tls generic-arch
# Preserve the existing package behavior, including pinned mold's allocator.
PKG_SUGGESTED_OPTIONS=	malloc-override
# NetBSD packages must run on the baseline CPU for their target ABI.
PKG_SUGGESTED_OPTIONS.NetBSD+=	generic-arch

.include "../../mk/bsd.options.mk"

.if ${PKG_OPTIONS:Mmalloc-override}
CMAKE_CONFIGURE_ARGS+=	-DMI_OVERRIDE=ON
.else
CMAKE_CONFIGURE_ARGS+=	-DMI_OVERRIDE=OFF
.endif
.if ${PKG_OPTIONS:Mdynamic-tls}
CMAKE_CONFIGURE_ARGS+=	-DMI_TLS_MODEL=LOCAL_DYNAMIC
.else
CMAKE_CONFIGURE_ARGS+=	-DMI_TLS_MODEL=DEFAULT
.endif
.if ${PKG_OPTIONS:Mgeneric-arch}
CMAKE_CONFIGURE_ARGS+=	-DMI_OPT_ARCH=OFF
.else
CMAKE_CONFIGURE_ARGS+=	-DMI_OPT_ARCH=DEFAULT
.endif

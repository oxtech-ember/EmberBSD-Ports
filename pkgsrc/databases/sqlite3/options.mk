# $NetBSD: options.mk,v 1.10 2025/03/30 06:18:06 adam Exp $

PKG_OPTIONS_VAR=		PKG_OPTIONS.sqlite3
PKG_SUPPORTED_OPTIONS=		icu readline

# EmberBSD: on a Darwin build host, readline selects the editline package.
# Its autotools chain needs Python, and Python needs SQLite. The native
# Darwin host CLI therefore has no line editing by default.
.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} != "Darwin"
PKG_SUGGESTED_OPTIONS=		readline
.endif

.include "../../mk/bsd.options.mk"

.if ${PKG_OPTIONS:Micu}
CONFIGURE_ARGS+=	--icu-collations
CONFIGURE_ARGS+=	--with-icu-ldflags='-licui18n -licuuc -licudata'
.include "../../textproc/icu/buildlink3.mk"
.endif

.if ${PKG_OPTIONS:Mreadline}
.include "../../mk/readline.buildlink3.mk"
.else
CONFIGURE_ARGS+=	--disable-readline
.endif

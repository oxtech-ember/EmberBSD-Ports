# $NetBSD: options.mk,v 1.20 2026/07/27 11:07:02 wiz Exp $

PKG_OPTIONS_VAR=	PKG_OPTIONS.groff
PKG_SUPPORTED_OPTIONS=	groff-docs uchardet x11
PKG_SUGGESTED_OPTIONS=	groff-docs x11

.include "../../mk/bsd.options.mk"

.if !empty(PKG_OPTIONS:Mgroff-docs)
# Consequently, groff's HTML output driver, 'grohtml', will not work
# properly.  It will not be possible to prepare or install
# groff-generated documentation in HTML format.
.  if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# Origin: EmberBSD (AI-assisted). The documentation build runs gs on the
# build host, and the installed devhtml DESC names the image generator that
# grohtml runs from PATH on the target. pkgsrc refuses the build-host gs as a
# target runtime tool, so a cross build uses it at build time, records the
# name "gs" and depends on the target Ghostscript package.
USE_TOOLS+=		gs
CONFIGURE_ARGS+=	--with-gs=gs
DEPENDS+=		ghostscript>=${GHOSTSCRIPT_REQD}:../../print/ghostscript
.  else
USE_TOOLS+=		gs:run
.  endif
PLIST_SRC+=		PLIST.docs
DEPENDS+=		netpbm>=10.0:../../graphics/netpbm
.else
CONFIGURE_ARGS+=	--without-gs
.endif

.if !empty(PKG_OPTIONS:Muchardet)
# The 'preconv' preprocessor program will be unable to attempt automatic
# inference of an input file's character encoding.  See the preconv(1)
# man page.
.include "../../textproc/uchardet/buildlink3.mk"
.endif

.if !empty(PKG_OPTIONS:Mx11)
CONFIGURE_ARGS+=	--with-x
CONFIGURE_ARGS+=	--with-appresdir=${PREFIX}/lib/X11/app-defaults
PLIST_SRC+=		PLIST.x11
.include "../../mk/xaw.buildlink3.mk"
.else
CONFIGURE_ARGS+=	--without-x
.endif

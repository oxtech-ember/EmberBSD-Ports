# $NetBSD: Makefile,v 1.36 2024/11/17 07:21:09 wiz Exp $

DISTNAME=		libXt-1.3.1
PKGREVISION=		2
CATEGORIES=		x11 devel
MASTER_SITES=		${MASTER_SITE_XORG:=lib/}
EXTRACT_SUFX=		.tar.xz

MAINTAINER=		pkgsrc-users@NetBSD.org
HOMEPAGE=		https://xorg.freedesktop.org/
COMMENT=		X Toolkit Intrinsics library
LICENSE=		mit

GNU_CONFIGURE=		yes
USE_LIBTOOL=		yes
TOOL_DEPENDS+=		xorg-util-macros>=1.20.2:../../devel/xorg-util-macros
USE_TOOLS+=		pkg-config autoconf automake

CONFIGURE_ARGS+=	--with-appdefaultdir=${PREFIX}/lib/X11/app-defaults
CONFIGURE_ENV+=		APP_MAN_SUFFIX=1 LIB_MAN_SUFFIX=3
PKGCONFIG_OVERRIDE+=	xt.pc.in

CONFIGURE_ARGS.NetBSD+=	--disable-malloc0returnsnull

.include "../../mk/bsd.prefs.mk"

.if ${USE_CROSS_COMPILE:U:tl} == yes
# The common cross profile supplies the native compiler command. makestrs
# only uses libc headers; target PREFIX headers do not belong in this build.
# Origin: EmberBSD (AI-assisted); preserve other pkgsrc cross configurations.
.  if defined(EMBERBSD_CROSS_BUILD_CC)
CONFIGURE_ENV+=	CC_FOR_BUILD=${NATIVE_CC:Q} CPPFLAGS_FOR_BUILD=
.  else
CONFIGURE_ENV+=	CC_FOR_BUILD=${NATIVE_CC:Q} CPPFLAGS_FOR_BUILD=-I${PREFIX}/include
.  endif
.endif

CPPFLAGS.OSF1+=		-pthread # Required by compiler if including pthread.h

.include "../../mk/compiler.mk"

TOOL_DEPENDS+=		tradcpp-[0-9]*:../../devel/tradcpp
CONFIGURE_ENV+=		ac_cv_path_RAWCPP="${TOOLBASE}/bin/tradcpp -Uunix"

X11_LIB_NAME?=		libXt
.include "../../meta-pkgs/modular-xorg/avoid-duplicate.mk"
.include "../../x11/libSM/buildlink3.mk"
.include "../../x11/libICE/buildlink3.mk"
BUILDLINK_API_DEPENDS.libX11+= libX11>=1.8.14nb1
.include "../../x11/libX11/buildlink3.mk"
.include "../../x11/xorgproto/buildlink3.mk"
# Regenerate changed Autoconf inputs with selected host tools.
pre-configure:
	cd ${WRKSRC} && aclocal -I m4 && autoheader && autoconf

.include "../../mk/bsd.pkg.mk"

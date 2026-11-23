# $NetBSD: Makefile,v 1.127 2026/09/02 19:03:04 wiz Exp $

DISTNAME=	ibus-1.5.35
PKGNAME=	${DISTNAME:S/-rc/rc/:S/-beta/beta/}
PKGREVISION=	1
CATEGORIES=	inputmethod
MASTER_SITES=	${MASTER_SITE_GITHUB:=ibus/}
GITHUB_PROJECT=	${PKGBASE}
GITHUB_RELEASE=	${DISTNAME:S/${PKGBASE}-//}

MAINTAINER=	tsutsui@NetBSD.org
HOMEPAGE=	https://github.com/ibus/ibus/wiki
LICENSE=	gnu-lgpl-v2.1
COMMENT=	Intelligent Input Bus

TOOL_DEPENDS+=	cldr-emoji-annotation>=37.0.13.0.0.2:../../textproc/cldr-emoji-annotation
TOOL_DEPENDS+=	unicode-character-database>=18.0.0:../../textproc/unicode-character-database
TOOL_DEPENDS+=	unicode-emoji>=18.0:../../textproc/unicode-emoji

GNU_CONFIGURE=			yes
USE_LIBTOOL=			yes
USE_TOOLS+=			pkg-config intltool msgfmt gmake msgmerge
# To regenarete portal/ibus-portal-dbus.[ch] to sync with system glib2 version
USE_TOOLS+=			gdbus-codegen
USE_LANGUAGES=			c c++
USE_PKGLOCALEDIR=		yes

PKGCONFIG_OVERRIDE+=	ibus-1.0.pc.in

CONFIGURE_ARGS+=	--sysconfdir=${PKG_SYSCONFBASEDIR}
CONFIGURE_ARGS+=	--localedir=${PREFIX}/${PKGLOCALEDIR}/locale
CONFIGURE_ARGS+=	--enable-dconf
CONFIGURE_ARGS+=	--enable-surrounding-text
CONFIGURE_ARGS+=	--disable-systemd-services
IBUS_HOST_UNICODE_DATA?=	${TOOLBASE}/share/unicode
CONFIGURE_ARGS+=	--with-unicode-emoji-dir=${IBUS_HOST_UNICODE_DATA:Q}/emoji
CONFIGURE_ARGS+=	--with-emoji-annotation-dir=${IBUS_HOST_UNICODE_DATA:Q}/cldr/common/annotations
CONFIGURE_ARGS+=	--with-ucd-dir=${IBUS_HOST_UNICODE_DATA:Q}/ucd

.include "../../mk/bsd.prefs.mk"
.include "options.mk"

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
TOOL_DEPENDS+=	glib2-[0-9]*:../../devel/glib2
TOOL_DEPENDS+=	libtool-base-[0-9]*:../../devel/libtool-base
TOOL_DEPENDS+=	vala>=0.56.13nb1:../../lang/vala
TOOLS_CREATE+=	ibus-pkg-config-for-build
TOOLS_SCRIPT.ibus-pkg-config-for-build= \
	exec ${SETENV} PKG_CONFIG_PATH= PKG_CONFIG_SYSROOT_DIR= \
	PKG_CONFIG_LIBDIR=${TOOLBASE:Q}/lib/pkgconfig:${TOOLBASE:Q}/share/pkgconfig \
	${TOOLBASE:Q}/bin/pkg-config "$$@"
CONFIGURE_ENV+=	PKG_CONFIG_FOR_BUILD=${TOOLS_DIR:Q}/bin/ibus-pkg-config-for-build
CONFIGURE_ENV+=	GLIB_GENMARSHAL=${TOOLBASE:Q}/bin/glib-genmarshal
CONFIGURE_ENV+=	VALAC=${TOOLBASE:Q}/bin/valac-0.56
CONFIGURE_ENV+=	VAPIGEN=${TOOLBASE:Q}/bin/vapigen-0.56
# GLib's gi18n-lib.h used by the native Compose generator includes libintl.h.
TOOL_DEPENDS+=	gettext-lib>=1.0:../../devel/gettext-lib
CPPFLAGS_FOR_BUILD+=	-I${TOOLBASE:Q}/include/gettext
LDFLAGS_FOR_BUILD+=	-L${TOOLBASE:Q}/lib
.  if ${NATIVE_OPSYS} == "Darwin"
# The Compose table generator runs from WRKSRC and links the host GLib.
LDFLAGS_FOR_BUILD+=	-Wl,-rpath,${TOOLBASE:Q}/lib
.  endif
CONFIGURE_ENV+=	CPPFLAGS_FOR_BUILD=${CPPFLAGS_FOR_BUILD:Q}
CONFIGURE_ENV+=	LDFLAGS_FOR_BUILD=${LDFLAGS_FOR_BUILD:Q}
MAKE_ENV+=	LIBTOOL_FOR_BUILD=${TOOLBASE:Q}/bin/libtool
.for generator in GDBUS_CODEGEN GLIB_COMPILE_RESOURCES GLIB_GENMARSHAL GLIB_MKENUMS
MAKE_FLAGS+=	${generator}=${TOOLBASE:Q}/bin/${generator:tl:S/_/-/g}
.endfor
# The runtime records the target path. Only the host generator prepends the sysroot.
CONFIGURE_ENV+=	IBUS_BUILD_SYSROOT=${CROSS_DESTDIR:Q}
MAKE_ENV+=	IBUS_BUILD_SYSROOT=${CROSS_DESTDIR:Q}
CONFIGURE_ARGS+=	--with-python=${TOOL_PYTHONBIN}
CONFIGURE_ARGS+=	--disable-tests
.else
CONFIGURE_ARGS+=	--with-python=${PYTHONBIN}
.include "../../lang/vala/buildlink3.mk"
.endif

# XXX lack of dbusmenu-glib
CONFIGURE_ARGS+=	--disable-appindicator

# avoid generating "*.cpython3*.opt-2.pyc" by -OO on byte compiling
# https://mail-index.netbsd.org/pkgsrc-users/2025/04/17/msg041482.html
SUBST_CLASSES+=		pyopt
SUBST_MESSAGE.pyopt=	Fixing Python byte compile optimization level.
SUBST_STAGE.pyopt=	pre-configure
SUBST_FILES.pyopt=	py-compile
SUBST_SED.pyopt=	-e 's/ -OO / -O /g'

SUBST_CLASSES+=		dbus
SUBST_STAGE.dbus=	post-configure
SUBST_FILES.dbus=	src/ibusshare.c
SUBST_SED.dbus=		-e 's,/var/lib/dbus/machine-id,${VARBASE}/lib/dbus/machine-id,g'

BUILD_DEFS+=		PKG_SYSCONFBASE VARBASE
MANCOMPRESSED=		yes

INSTALL_MAKE_FLAGS+=	sysconfdir=${PREFIX}/share/examples/ibus
MAKE_DIRS+=		${PKG_SYSCONFDIR}/dconf/db/ibus.d
MAKE_DIRS+=		${PKG_SYSCONFDIR}/dconf/profile
CONF_FILES+=		${PREFIX}/share/examples/ibus/dconf/db/ibus.d/00-upstream-settings \
			${PKG_SYSCONFDIR}/dconf/db/ibus.d/00-upstream-settings
CONF_FILES+=		${PREFIX}/share/examples/ibus/dconf/profile/ibus \
			${PKG_SYSCONFDIR}/dconf/profile/ibus

.include "../../mk/compiler.mk"
.if ${CC_VERSION:Mgcc-4.1.[0-9]*}
BUILDLINK_TRANSFORM+=	rm:-Wno-unused-but-set-variable
.endif

# wayland or not
PLIST_VARS+=		wayland
.include "../../devel/wayland/platform.mk"
.if ${PLATFORM_SUPPORTS_WAYLAND} == "yes"
CONFIGURE_ARGS+=	--enable-wayland
.  if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
TOOL_DEPENDS+=	wayland-[0-9]*:../../devel/wayland
MAKE_FLAGS+=	wayland_scanner=${TOOLBASE:Q}/bin/wayland-scanner
.  endif
PLIST.wayland=		yes
.  if !empty(PKG_OPTIONS:Mgtk3)
PLIST.gtk3wayland=	yes
.  endif
.else
CONFIGURE_ARGS+=	--disable-wayland
.endif

# Explicitly regenerate .c sources from .vala where the generated sources
# depend on configure result.  Generated sources in the distfile may have
# been created with different options.
# See also https://github.com/ibus/ibus/issues/2767
#
# Also make sure to regenerate portal/ibus-portal-dbus.[ch] to
# sync with system glib2 version.
pre-build:
.if !empty(PKG_OPTIONS:Mgtk3)
	(cd ${WRKSRC} && ${MAKE_PROGRAM} -C ui/gtk3 maintainer-clean-generic)
.endif
	(cd ${WRKSRC} && ${MAKE_PROGRAM} -C tools maintainer-clean-generic)
	(cd ${WRKSRC} && ${MAKE_PROGRAM} -C portal maintainer-clean-generic)

.include "../../devel/glib2/schemas.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# IBus validates each schema during the build with --strict --dry-run.
MAKE_FLAGS+=	GLIB_COMPILE_SCHEMAS=${TOOLBASE:Q}/bin/glib-compile-schemas
.endif
.include "../../devel/dconf/database.mk"
.include "../../devel/dconf/buildlink3.mk"
.include "../../devel/gettext-tools/msgfmt-desktop.mk"
.include "../../devel/gettext-lib/buildlink3.mk"
BUILDLINK_API_DEPENDS.glib2+=		glib2>=2.46.0
.include "../../devel/glib2/buildlink3.mk"
.include "../../graphics/hicolor-icon-theme/buildlink3.mk"
PY_PATCHPLIST=	yes
.include "../../sysutils/dbus/buildlink3.mk"
.include "../../sysutils/libnotify/buildlink3.mk"
.include "../../textproc/iso-codes/buildlink3.mk"
.include "../../x11/libX11/buildlink3.mk"
.include "../../lang/python/extension.mk"
.include "../../mk/bsd.pkg.mk"

# $NetBSD: Makefile,v 1.127 2026/09/02 19:03:04 wiz Exp $

DISTNAME=	ibus-1.5.34
PKGNAME=	${DISTNAME:S/-rc/rc/:S/-beta/beta/}
PKGREVISION=	3
CATEGORIES=	inputmethod
MASTER_SITES=	${MASTER_SITE_GITHUB:=ibus/}
GITHUB_PROJECT=	${PKGBASE}
GITHUB_RELEASE=	${DISTNAME:S/${PKGBASE}-//}

MAINTAINER=	tsutsui@NetBSD.org
HOMEPAGE=	https://github.com/ibus/ibus/wiki
LICENSE=	gnu-lgpl-v2.1
COMMENT=	Intelligent Input Bus

TOOL_DEPENDS+=	glib2-introspection-[0-9]*:../../devel/glib2-introspection
# Cross probe: python GObject bindings need a target interpreter.
# The Python method engine is optional; the daemon does not require it.
TOOL_DEPENDS+=	cldr-emoji-annotation>=37.0.13.0.0.2:../../textproc/cldr-emoji-annotation
TOOL_DEPENDS+=	unicode-character-database>=15.0.0:../../textproc/unicode-character-database
TOOL_DEPENDS+=	unicode-emoji>=15.0:../../textproc/unicode-emoji

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
CONFIGURE_ARGS+=	--disable-gtk2
# GTK4 profile: the panel UI is GTK3/Vala only and is not built.
# XIM would pull a gtk2 requirement when gtk3 is off; Wayland/GTK4 does not use XIM.
CONFIGURE_ARGS+=	--disable-gtk3
CONFIGURE_ARGS+=	--enable-gtk4
CONFIGURE_ARGS+=	--disable-ui
CONFIGURE_ARGS+=	--disable-xim
# Cross: test programs cannot run on the host; they also link X11 unconditionally.
CONFIGURE_ARGS+=	--disable-tests
CONFIGURE_ARGS+=	--enable-surrounding-text
CONFIGURE_ARGS+=	--enable-introspection=no
CONFIGURE_ARGS+=	--disable-systemd-services
# Cross: build-time generators run on the host with the host glib.
CONFIGURE_ENV+=	GLIB_GENMARSHAL=/private/tmp/ember-common-stack/host/bin/glib-genmarshal
CFLAGS_FOR_BUILD+=	-I/private/tmp/ember-common-stack/host/include/glib-2.0 -I/private/tmp/ember-common-stack/host/lib/glib-2.0/include
CPPFLAGS_FOR_BUILD+=	-I/private/tmp/ember-common-stack/host/include/glib-2.0 -I/private/tmp/ember-common-stack/host/lib/glib-2.0/include
LDFLAGS_FOR_BUILD+=	-L/private/tmp/ember-common-stack/host/lib
# Cross: the version probe must run on the host; the engine still targets python3.14 at runtime.
CONFIGURE_ARGS+=	--with-python=/private/tmp/ember-common-stack/host/bin/python3.14
CONFIGURE_ARGS+=	--with-unicode-emoji-dir=/private/tmp/ember-common-stack/host/share/unicode/emoji
CONFIGURE_ARGS+=	--with-emoji-annotation-dir=/private/tmp/ember-common-stack/host/share/unicode/cldr/common/annotations
CONFIGURE_ARGS+=	--with-ucd-dir=/private/tmp/ember-common-stack/host/share/unicode/ucd

# XXX lack of dbusmenu-glib
CONFIGURE_ARGS+=	--disable-appindicator

# avoid generating "*.cpython3*.opt-2.pyc" by -OO on byte compiling
# https://mail-index.netbsd.org/pkgsrc-users/2025/04/17/msg041482.html
SUBST_CLASSES+=		pyopt
SUBST_MESSAGE.pyopt=	Fixing Python byte compile optimization level.
SUBST_STAGE.pyopt=	pre-configure
SUBST_FILES.pyopt=	py-compile
SUBST_SED.pyopt=	-e 's/ -OO / -O /g'

# Cross: the runtime setup script must not embed the build-time host python.
SUBST_CLASSES+=		python-runtime
SUBST_MESSAGE.python-runtime=	Fixing runtime python path in ibus-setup.
SUBST_STAGE.python-runtime=	post-configure
SUBST_FILES.python-runtime=	setup/ibus-setup
SUBST_SED.python-runtime=	-e "s,/private/tmp/ember-common-stack/host/bin/python3.14,/usr/pkg/bin/python3.14,g"

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
PLIST.wayland=		yes
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
	(cd ${WRKSRC} && ${MAKE_PROGRAM} -C tools maintainer-clean-generic)
	(cd ${WRKSRC} && ${MAKE_PROGRAM} -C portal maintainer-clean-generic)

.include "../../devel/glib2/schemas.mk"
.include "../../devel/dconf/database.mk"
.include "../../devel/dconf/buildlink3.mk"
.include "../../devel/gettext-tools/msgfmt-desktop.mk"
BUILDLINK_API_DEPENDS.gobject-introspection+=	gobject-introspection>=0.9.6
BUILDLINK_DEPMETHOD.gobject-introspection+=	build
.include "../../devel/gobject-introspection/buildlink3.mk"
.include "../../devel/gettext-lib/buildlink3.mk"
BUILDLINK_API_DEPENDS.glib2+=		glib2>=2.46.0
.include "../../devel/glib2/buildlink3.mk"
.include "../../graphics/hicolor-icon-theme/buildlink3.mk"
.include "../../lang/vala/buildlink3.mk"
PY_PATCHPLIST=	yes
.include "../../sysutils/dbus/buildlink3.mk"
.include "../../sysutils/libnotify/buildlink3.mk"
.include "../../textproc/iso-codes/buildlink3.mk"
BUILDLINK_API_DEPENDS.gtk4+=		gtk4>=4.14.0
.include "../../x11/gtk4/buildlink3.mk"
.include "../../x11/libX11/buildlink3.mk"
.include "../../lang/python/extension.mk"
.include "../../mk/bsd.pkg.mk"

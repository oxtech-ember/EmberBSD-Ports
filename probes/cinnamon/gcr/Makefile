# gcr (gcr-base part) for the Cinnamon shell keyring prompt.
# Cinnamon probe copy of security/gcr: the GTK3 UI library (gcr-ui-3,
# gcr-3) is not built - the profile carries no GTK3 - and only the
# gcr-base-3 library with introspection is installed.
DISTNAME=	gcr-3.41.2
PKGREVISION=	1
CATEGORIES=	security
MASTER_SITES=	${MASTER_SITE_GNOME:=sources/${PKGBASE}/${PKGVERSION_NOREV:R}/}
EXTRACT_SUFX=	.tar.xz

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://www.gnome.org/
COMMENT=	Library for crypto UI and related tasks (gcr-base only)
LICENSE=	gnu-gpl-v2

TOOL_DEPENDS+=	gettext-m4-[0-9]*:../../devel/gettext-m4
TOOL_DEPENDS+=	glib2-introspection-[0-9]*:../../devel/glib2-introspection
DEPENDS+=	gnupg2-[0-9]*:../../security/gnupg2

USE_TOOLS+=	gdbus-codegen intltool msgfmt perl pkg-config readlink

CPPFLAGS.NetBSD+=	-D_NETBSD_SOURCE

MESON_ARGS=		-Dsystemd=disabled
# Cross: documentation toolchain stays off.
MESON_ARGS+=		-Dgtk_doc=false

PKGCONFIG_OVERRIDE_STAGE=	pre-install
PKGCONFIG_OVERRIDE+=		output/meson-private/gck-1.pc \
			output/meson-private/gcr-base-3.pc

REPLACE_PYTHON=		meson_post_install.py

# Gck-1/Gcr typelibs are imported by the shell keyring prompt.
EMBERBSD_GI_MESON_OPTIONS= no
.include "../../devel/gobject-introspection/cross.mk"
MESON_ARGS+=	-Dgi_cross_use_prebuilt_gi=true
MESON_ARGS+=	-Dgi_cross_ldd_wrapper=${EMBERBSD_GI_FILESDIR}/elf-needed.sh
MESON_CROSS_VARS+= emberbsd_gi_cross emberbsd_gi_ldd_wrapper
MESON_CROSS.emberbsd_gi_cross= true
MESON_CROSS.emberbsd_gi_ldd_wrapper= '${EMBERBSD_GI_FILESDIR}/elf-needed.sh'
MESON_BINARIES+= g-ir-scanner g-ir-compiler
MESON_BINARY.g-ir-scanner= ${TOOLBASE}/bin/g-ir-scanner
MESON_BINARY.g-ir-compiler= ${TOOLBASE}/bin/g-ir-compiler
MAKE_ENV+= XDG_DATA_DIRS=${CROSS_DESTDIR:Q}${PREFIX:Q}/share

.include "../../devel/gettext-tools/msgfmt-desktop.mk"
.include "../../devel/glib2/buildlink3.mk"
.include "../../devel/gobject-introspection/buildlink3.mk"
.include "../../devel/meson/build.mk"
.include "../../graphics/hicolor-icon-theme/buildlink3.mk"
.include "../../lang/python/application.mk"
.include "../../security/libgcrypt/buildlink3.mk"
.include "../../security/libsecret/buildlink3.mk"
.include "../../security/p11-kit/buildlink3.mk"
.include "../../sysutils/desktop-file-utils/desktopdb.mk"
.include "../../mk/bsd.pkg.mk"

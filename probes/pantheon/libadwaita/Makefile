# $NetBSD$

DISTNAME=	libadwaita-1.9.4
CATEGORIES=	x11 gnome
MASTER_SITES=	${MASTER_SITE_GNOME:=sources/libadwaita/1.9/}
EXTRACT_SUFX=	.tar.xz

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://gitlab.gnome.org/GNOME/libadwaita
COMMENT=	Companion library to GTK4 with GNOME design patterns
LICENSE=	gnu-lgpl-v2.1

USE_TOOLS+=	pkg-config msgfmt

MESON_ARGS+=	-Dtests=false
MESON_ARGS+=	-Dexamples=false
MESON_ARGS+=	-Ddocumentation=false

.include "../../mk/bsd.prefs.mk"

# Cross: introspection + vapi through the shared GI cross machinery
# (host generators, real target GType queries over SSH) as in pango.
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
BUILD_DEPENDS+= glib2-introspection>=2.90.1nb1:../../devel/glib2-introspection
.undef EMBERBSD_GI_MESON_OPTIONS
EMBERBSD_GI_MESON_OPTIONS= no
.include "../../devel/gobject-introspection/cross.mk"
MAKE_ENV+= XDG_DATA_DIRS=${CROSS_DESTDIR:Q}${PREFIX:Q}/share
_EMBERBSD_GI_REAL_SYSROOT!= cd ${CROSS_DESTDIR:Q} && pwd -P
BUILDLINK_TRANSFORM+= I:${_EMBERBSD_GI_REAL_SYSROOT}${PREFIX}:${BUILDLINK_DIR}
MESON_BINARIES+= g-ir-scanner g-ir-compiler
MESON_BINARY.g-ir-scanner= ${TOOLBASE}/bin/g-ir-scanner
MESON_BINARY.g-ir-compiler= ${TOOLBASE}/bin/g-ir-compiler
MESON_CROSS_VARS+= emberbsd_gi_cross emberbsd_gi_ldd_wrapper
MESON_CROSS.emberbsd_gi_cross= true
MESON_CROSS.emberbsd_gi_ldd_wrapper= '${EMBERBSD_GI_FILESDIR}/elf-needed.sh'
# Cross: the GIR introspect binary links with the target sysroot paths.
LDFLAGS+=	-L/private/tmp/ember-common-stack/sysroot/usr/pkg/lib
BUILDLINK_DEPMETHOD.gobject-introspection=	build
BUILDLINK_API_DEPENDS.gobject-introspection+=	gobject-introspection>=1.86.0nb5
# Cross: the pkgsrc buildlink scan does not lift the GI pkg-config file;
# gnome.generate_gir resolves gobject-introspection-1.0 for the target.
pre-configure: emberbsd-adw-gi-pc
.PHONY: emberbsd-adw-gi-pc
emberbsd-adw-gi-pc:
	${RUN}${CP} ${CROSS_DESTDIR}${PREFIX}/lib/pkgconfig/gobject-introspection-1.0.pc \
		${BUILDLINK_DIR}/lib/pkgconfig/
	${RUN}for l in libgirepository-1.0.so libgirepository-1.0.so.1 \
		libgirepository-1.0.so.1.0.0; do \
		${LN} -sf ${CROSS_DESTDIR}${PREFIX}/lib/$$l ${BUILDLINK_DIR}/lib/$$l; \
	done
MESON_ARGS+=	-Dintrospection=enabled -Dvapi=true
.else
MESON_ARGS+=	-Dintrospection=disabled -Dvapi=false
.endif

.include "../../devel/glib2/buildlink3.mk"
.include "../../devel/meson/build.mk"
.include "../../converters/fribidi/buildlink3.mk"
.include "../../devel/appstream/buildlink3.mk"
.include "../../x11/gtk4/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

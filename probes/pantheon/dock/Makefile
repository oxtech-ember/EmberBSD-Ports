# $NetBSD$

DISTNAME=	dock-8.3.3
CATEGORIES=	x11
MASTER_SITES=	${MASTER_SITE_GITHUB:=elementary/}
GITHUB_RELEASE=	8.3.3

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/elementary/dock
COMMENT=	Elementary dock and applications launcher (GTK4 plank successor)
LICENSE=	gnu-gpl-v3

USE_TOOLS+=	pkg-config msgfmt

MESON_ARGS+=	-Dworkspace-switcher=true

.include "../../converters/fribidi/buildlink3.mk"
.include "../../databases/sqlite3/buildlink3.mk"
.include "../../devel/glib2/buildlink3.mk"
.include "../../devel/libgee/buildlink3.mk"
.include "../../devel/meson/build.mk"
.include "../../fonts/harfbuzz/buildlink3.mk"
.include "../../graphics/cairo/buildlink3.mk"
.include "../../graphics/graphene/buildlink3.mk"
.include "../../textproc/libxmlb/buildlink3.mk"
.include "../../x11/gtk4/buildlink3.mk"
.include "../../x11/granite/buildlink3.mk"
.include "../../x11/libadwaita/buildlink3.mk"
.include "../../devel/appstream/buildlink3.mk"
.include "../../x11/libX11/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

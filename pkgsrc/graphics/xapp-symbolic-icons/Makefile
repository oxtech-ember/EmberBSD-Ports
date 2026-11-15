# XApp symbolic icons, upstream 1.1.2
DISTNAME= xapp-symbolic-icons-1.1.2
CATEGORIES= graphics
MASTER_SITES= ${MASTER_SITE_GITHUB:=xapp-project/}
GITHUB_TAG= ${PKGVERSION_NOREV}

MAINTAINER= oxtech-ember@users.noreply.github.com
HOMEPAGE= https://github.com/xapp-project/xapp-symbolic-icons
COMMENT= Symbolic icons for XApp and GTK applications
LICENSE= gnu-lgpl-v3

USE_LANGUAGES= # none
NO_ARCH= yes
REPLACE_PYTHON+= icons/xsi-replace-adwaita-symbolic.in

.include "../../graphics/hicolor-icon-theme/buildlink3.mk"
.include "../../lang/python/application.mk"
.include "../../devel/meson/build.mk"
.include "../../mk/bsd.pkg.mk"

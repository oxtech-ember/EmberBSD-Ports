# Web App Manager 1.4.7, upstream commit 557a5956b7c5d6c9993e6578ec6dd6e60f4659d9.
# Local portability and Ember Browser integration prepared with AI assistance.
DISTNAME= webapp-manager-1.4.7
CATEGORIES= www
MASTER_SITES= https://github.com/linuxmint/webapp-manager/archive/
DISTFILES= 557a5956b7c5d6c9993e6578ec6dd6e60f4659d9.tar.gz
DIST_SUBDIR= webapp-manager
WRKSRC= ${WRKDIR}/webapp-manager-557a5956b7c5d6c9993e6578ec6dd6e60f4659d9

MAINTAINER= oxtech-ember@users.noreply.github.com
HOMEPAGE= https://github.com/linuxmint/webapp-manager
COMMENT= Run websites as desktop applications
LICENSE= gnu-gpl-v3

DEPENDS+= ${PYPKGPREFIX}-gobject3-[0-9]*:../../devel/py-gobject3
DEPENDS+= ${PYPKGPREFIX}-cairo-[0-9]*:../../graphics/py-cairo
DEPENDS+= ${PYPKGPREFIX}-Pillow-[0-9]*:../../graphics/py-Pillow
DEPENDS+= ${PYPKGPREFIX}-requests-[0-9]*:../../devel/py-requests
DEPENDS+= ${PYPKGPREFIX}-beautifulsoup4-[0-9]*:../../www/py-beautifulsoup4
DEPENDS+= ${PYPKGPREFIX}-setproctitle-[0-9]*:../../sysutils/py-setproctitle
DEPENDS+= ${PYPKGPREFIX}-tldextract-[0-9]*:../../net/py-tldextract
DEPENDS+= gtk3+-[0-9]*:../../x11/gtk3
DEPENDS+= ember-browser>=1.46.0nb9:../../www/blanc
DEPENDS+= xapp-[0-9]*:../../x11/xapp
DEPENDS+= xapp-symbolic-icons-[0-9]*:../../graphics/xapp-symbolic-icons
USE_LANGUAGES= # none
USE_TOOLS+= msgfmt pax
NO_BUILD= yes
PYTHON_FOR_BUILD_ONLY= no
SUBST_CLASSES+= prefix
SUBST_STAGE.prefix= pre-configure
SUBST_FILES.prefix= usr/lib/webapp-manager/common.py usr/lib/webapp-manager/webapp-manager.py
SUBST_VARS.prefix= PREFIX
REPLACE_PYTHON+= usr/lib/webapp-manager/webapp-manager.py

CONF_FILES+= ${PREFIX}/share/examples/webapp-manager/webapps.menu \
 ${PKG_SYSCONFDIR}/xdg/menus/applications-merged/webapps.menu

INSTALLATION_DIRS= bin lib/webapp-manager share/applications/kde4 \
 share/desktop-directories share/glib-2.0/schemas share/icons/hicolor/scalable/apps \
 share/icons/hicolor/scalable/categories share/webapp-manager/firefox/profile/chrome \
 share/examples/webapp-manager

do-test:
	${TOOL_PYTHONBIN} ${FILESDIR}/launcher-test.py ${WRKSRC}

do-install:
	${INSTALL_SCRIPT} ${WRKSRC}/usr/lib/webapp-manager/webapp-manager.py ${DESTDIR}${PREFIX}/lib/webapp-manager/
	${INSTALL_DATA} ${WRKSRC}/usr/lib/webapp-manager/common.py ${DESTDIR}${PREFIX}/lib/webapp-manager/
	${PRINTF} '#!/bin/sh\nexec "%s/lib/webapp-manager/webapp-manager.py" "$$@"\n' ${PREFIX:Q} > ${WRKDIR}/webapp-manager
	${INSTALL_SCRIPT} ${WRKDIR}/webapp-manager ${DESTDIR}${PREFIX}/bin/
	cd ${WRKSRC}/usr/share && ${PAX} -rw -pp applications desktop-directories glib-2.0 icons webapp-manager ${DESTDIR}${PREFIX}/share
	${INSTALL_DATA} ${WRKSRC}/etc/xdg/menus/applications-merged/webapps.menu ${DESTDIR}${PREFIX}/share/examples/webapp-manager/
	for f in ${WRKSRC}/po/*.po; do \
	  lang=$${f##*/webapp-manager-}; lang=$${lang%.po}; \
	  ${INSTALL_DATA_DIR} ${DESTDIR}${PREFIX}/share/locale/$$lang/LC_MESSAGES; \
	  ${TOOLS_PATH.msgfmt} -o ${DESTDIR}${PREFIX}/share/locale/$$lang/LC_MESSAGES/webapp-manager.mo $$f; \
	done

.include "../../lang/python/application.mk"
.include "../../devel/glib2/schemas.mk"
.include "../../sysutils/desktop-file-utils/desktopdb.mk"
.include "../../mk/bsd.pkg.mk"

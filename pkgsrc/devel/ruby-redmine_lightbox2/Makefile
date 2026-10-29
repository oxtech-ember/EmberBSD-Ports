# $NetBSD$
#

DISTNAME=	${GITHUB_TAG}
PKGNAME=	${RUBY_PKGPREFIX}-${PLUGIN_NAME:S/redmine_/redmine${RM_VER}-/}-${DISTNAME:S/v//1}
MASTER_SITES=	${MASTER_SITE_GITHUB:=paginagmbh/}
GITHUB_PROJECT=	${PLUGIN_NAME}
GITHUB_TAG=	v0.5.1
PKGREVISION=	1
DIST_SUBDIR=	ruby-${PLUGIN_NAME}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/paginagmbh/redmine_lightbox2
COMMENT=	Lightbox for image attachments in Redmine
LICENSE=	mit

PLUGIN_NAME=	redmine_lightbox2

.include "../../meta-pkgs/ruby-redmine-plugins/Makefile.common"

NO_CONFIGURE=	yes
NO_BUILD=	yes

LIGHTBOX2_PLUGIN_DIR=	${RM_PLUGINDIR}/redmine_lightbox2

INSTALLATION_DIRS+=	${LIGHTBOX2_PLUGIN_DIR}/app/views/attachments
INSTALLATION_DIRS+=	${LIGHTBOX2_PLUGIN_DIR}/assets/images
INSTALLATION_DIRS+=	${LIGHTBOX2_PLUGIN_DIR}/assets/javascripts
INSTALLATION_DIRS+=	${LIGHTBOX2_PLUGIN_DIR}/assets/stylesheets
INSTALLATION_DIRS+=	${LIGHTBOX2_PLUGIN_DIR}/config
INSTALLATION_DIRS+=	${LIGHTBOX2_PLUGIN_DIR}/lib/redmine_lightbox2/hooks
INSTALLATION_DIRS+=	${LIGHTBOX2_PLUGIN_DIR}/test

do-install:
	${INSTALL_DATA}	${WRKSRC}/init.rb \
		${DESTDIR}${PREFIX}/${LIGHTBOX2_PLUGIN_DIR}
	${INSTALL_DATA}	${WRKSRC}/app/views/attachments/*.erb \
		${DESTDIR}${PREFIX}/${LIGHTBOX2_PLUGIN_DIR}/app/views/attachments
	for i in images javascripts stylesheets; do \
		${INSTALL_DATA} ${WRKSRC}/assets/$$i/* \
			${DESTDIR}${PREFIX}/${LIGHTBOX2_PLUGIN_DIR}/assets/$$i; \
	done
	${INSTALL_DATA} ${WRKSRC}/config/routes.rb \
		 ${DESTDIR}${PREFIX}/${LIGHTBOX2_PLUGIN_DIR}/config
	${INSTALL_DATA} ${WRKSRC}/lib/redmine_lightbox2/*.rb \
		${DESTDIR}${PREFIX}/${LIGHTBOX2_PLUGIN_DIR}/lib/redmine_lightbox2
	${INSTALL_DATA} ${WRKSRC}/lib/redmine_lightbox2/hooks/*.rb \
		${DESTDIR}${PREFIX}/${LIGHTBOX2_PLUGIN_DIR}/lib/redmine_lightbox2/hooks
	${INSTALL_DATA} ${WRKSRC}/test/test_helper.rb \
		 ${DESTDIR}${PREFIX}/${LIGHTBOX2_PLUGIN_DIR}/test

.include "../../lang/ruby/rubyversion.mk"
.include "../../mk/bsd.pkg.mk"

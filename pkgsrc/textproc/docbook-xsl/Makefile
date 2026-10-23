# $NetBSD: Makefile,v 1.80 2023/09/28 22:12:12 joerg Exp $

DISTNAME=	docbook-xsl-nons-1.79.2
PKGNAME=	${DISTNAME:S/-nons//}
PKGREVISION=	8
CATEGORIES=	textproc
MASTER_SITES=	${MASTER_SITE_GITHUB:=docbook/}
GITHUB_PROJECT=	xslt10-stylesheets
GITHUB_RELEASE=	release/${PKGVERSION_NOREV}
EXTRACT_SUFX=	.tar.bz2

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/docbook/xslt10-stylesheets/
COMMENT=	Docbook XSL modular stylesheet

DEPENDS+=	docbook-xml>=4.2:../../textproc/docbook-xml

USE_LANGUAGES=	# empty
USE_TOOLS+=	pax
NO_BUILD=	yes

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# pdf2index is an installed target tool; it never executes during packaging.
DEPENDS+= perl>=5.44.0:../../lang/perl5
REPLACE_INTERPRETER+= target-perl
REPLACE.target-perl.old= .*perl[^[:space:]]*
REPLACE.target-perl.new= ${PREFIX}/bin/perl
REPLACE_FILES.target-perl= fo/pdf2index
.else
USE_TOOLS+= perl:run
REPLACE_PERL+= fo/pdf2index
.endif

EGDIR=		${PREFIX}/share/examples/docbook-xsl
XSLDIR=		${PREFIX}/share/xsl/docbook
XSLMODS+=	assembly
XSLMODS+=	common
#XSLMODS+=	doc # empty
#XSLMODS+=	docsrc # source f
XSLMODS+=	eclipse
XSLMODS+=	epub
XSLMODS+=	epub3
#XSLMODS+=	extensions # java tools
XSLMODS+=	fo
XSLMODS+=	highlighting
XSLMODS+=	html
XSLMODS+=	htmlhelp
XSLMODS+=	images
XSLMODS+=	javahelp
XSLMODS+=	lib
XSLMODS+=	manpages
XSLMODS+=	params
XSLMODS+=	profiling
XSLMODS+=	roundtrip
XSLMODS+=	slides
#XSLMODS+=	template # documentation
#XSLMODS+=	tests # test data
#XSLMODS+=	tools # java tools
#XSLMODS+=	webhelp # HTML help
XSLMODS+=	website
XSLMODS+=	xhtml-1_1
XSLMODS+=	xhtml
XSLMODS+=	xhtml5

XML_CATALOGS=	${XSLDIR}/catalog.xml

INSTALLATION_DIRS=	${EGDIR} ${XSLDIR}

CHECK_INTERPRETER_SKIP+=	share/xsl/docbook/epub/bin/dbtoepub

post-extract:
	${RM} -f ${${FIND} ${WRKSRC} -type d:L:sh:=/.gitignore}
	chmod -R g-w ${WRKSRC}

do-install:
	cd ${WRKSRC}/template && ${PAX} -rw -pp -pm * ${DESTDIR}${EGDIR}
	${INSTALL_DATA} ${WRKSRC}/VERSION ${DESTDIR}${XSLDIR}
	${INSTALL_DATA} ${WRKSRC}/VERSION.xsl ${DESTDIR}${XSLDIR}
	${INSTALL_DATA} ${WRKSRC}/catalog.xml ${DESTDIR}${XSLDIR}/catalog.xml
	${RUN} for d in ${XSLMODS}; do \
	    ${ECHO} "${INSTALL_DATA_DIR} ${DESTDIR}${XSLDIR}/$$d"; \
	    ${ECHO} "cd ${WRKSRC} && ${PAX} -rw -pp -pm $$d ${DESTDIR}${XSLDIR}/"; \
	    cd ${WRKSRC} && ${PAX} -rw -pp -pm $$d ${DESTDIR}${XSLDIR}/; \
	done
	${FIND} ${DESTDIR}${XSLDIR} -name '*.orig' -exec ${RM} {} \;

.include "../../textproc/xmlcatmgr/catalogs.mk"
.include "../../mk/bsd.pkg.mk"

# $NetBSD: Makefile,v 1.16 2026/09/06 10:05:12 markd Exp $


.include "Makefile.common"

COMMENT=	Documentation generation from docbook

.include "../../meta-pkgs/kde/kf6.mk"
.include "cross-tools.mk"

PLIST_VARS+=	generators
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
CMAKE_CONFIGURE_ARGS+= -DRELOCATABLE_DOCBOOK_FILES=ON
CMAKE_CONFIGURE_ARGS+= -DLIBXML2_XMLLINT_EXECUTABLE=${TOOLBASE:Q}/bin/xmllint
PLIST.generators=	yes
.else
# kf6-kdoctools-generators installs the native library, generators, DocBook
# data and CMake files. This package adds their translations. Generators
# before nb2 conflict with this package.
DEPENDS+=	kf6-kdoctools-generators>=${KF6VER}nb2:../../devel/kf6-kdoctools-generators
post-install:
	${RUN}cd ${DESTDIR}${PREFIX} && ${FIND} . \( -type f -o -type l \) \
	    ! -path './share/locale/*' ! -path './man/*/man*/*' \
	    -exec ${RM} -f {} +
	${RUN}cd ${DESTDIR}${PREFIX} && ${FIND} . -depth -type d -empty -exec ${RMDIR} {} \;
.endif


USE_TOOLS+=	msgmerge perl

TOOL_DEPENDS+=	p5-URI-[0-9]*:../../www/p5-URI
DEPENDS+=	docbook-xsl-[0-9]*:../../textproc/docbook-xsl

.include "../../archivers/kf6-karchive/buildlink3.mk"
.include "../../devel/kf6-ki18n/buildlink3.mk"
.include "../../textproc/libxslt/buildlink3.mk"
.include "../../textproc/libxml2/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

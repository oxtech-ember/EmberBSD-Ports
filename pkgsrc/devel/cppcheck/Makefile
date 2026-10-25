# Origin: EmberBSD contributors (AI-assisted).
DISTNAME= cppcheck-2.22.0
CATEGORIES= devel
MASTER_SITES= ${MASTER_SITE_GITHUB:=cppcheck-opensource/}
GITHUB_PROJECT= cppcheck
GITHUB_TAG= ${PKGVERSION_NOREV}

MAINTAINER= reed@reedmedia.net
HOMEPAGE= https://cppcheck.sourceforge.io/
COMMENT= Tool for static C/C++ code analysis
LICENSE= gnu-gpl-v3

TOOL_DEPENDS+= libxslt-[0-9]*:../../textproc/libxslt
TOOL_DEPENDS+= libxml2-[0-9]*:../../textproc/libxml2
TOOL_DEPENDS+= docbook-xsl-[0-9]*:../../textproc/docbook-xsl
DEPENDS+= ${PYPKGPREFIX}-pygments-[0-9]*:../../textproc/py-pygments
USE_LANGUAGES= c c++
USE_CXX_FEATURES= c++17
USE_TOOLS+= pkg-config
PYTHON_VERSIONS_INCOMPATIBLE= 27
REPLACE_PYTHON+= htmlreport/cppcheck-htmlreport

CMAKE_CONFIGURE_ARGS+= -DCMAKE_CXX_STANDARD:STRING=17
CMAKE_CONFIGURE_ARGS+= -DBUILD_CLI:BOOL=ON
CMAKE_CONFIGURE_ARGS+= -DBUILD_GUI:BOOL=OFF
CMAKE_CONFIGURE_ARGS+= -DCMAKE_MACOSX_BUNDLE:BOOL=OFF
CMAKE_CONFIGURE_ARGS+= -DBUILD_TESTING:BOOL=ON
CMAKE_CONFIGURE_ARGS+= -DHAVE_RULES:BOOL=ON
CMAKE_CONFIGURE_ARGS+= -DUSE_BUNDLED_TINYXML2:BOOL=OFF
CMAKE_CONFIGURE_ARGS+= -DUSE_BOOST:STRING=On
# Release sources contain the generated build descriptions.
# Keep dmake available without running a target maintainer tool in cross builds.
CMAKE_CONFIGURE_ARGS+= -DDISABLE_DMAKE:BOOL=ON
CMAKE_CONFIGURE_ARGS+= -DFILESDIR:PATH=${PREFIX}/share/cppcheck
CMAKE_CONFIGURE_ARGS+= -DPython_EXECUTABLE:FILEPATH=${TOOL_PYTHONBIN}
CMAKE_CONFIGURE_ARGS+= -DPKG_CONFIG_EXECUTABLE:FILEPATH=${TOOLS_CMD.pkg-config}
CMAKE_CONFIGURE_ARGS+= -DLIBXML2_XMLLINT_EXECUTABLE:FILEPATH=${TOOLBASE}/bin/xmllint
CMAKE_CONFIGURE_ARGS+= -DBUILD_MANPAGE:BOOL=ON
CMAKE_CONFIGURE_ARGS+= -DXSLTPROC:FILEPATH=${TOOLBASE}/bin/xsltproc
CMAKE_CONFIGURE_ARGS+= -DDB2MAN:FILEPATH=${TOOLBASE}/share/xsl/docbook/manpages/docbook.xsl
BUILD_TARGET= all man
TEST_TARGET= test
INSTALLATION_DIRS+= ${PKGMANDIR}/man1

.include "../../devel/cmake/build.mk"
.include "options.mk"

post-install: man-install
.PHONY: man-install
man-install:
	${INSTALL_MAN} ${WRKSRC}/${CMAKE_BUILD_DIR}/man/cppcheck.1 ${DESTDIR}${PREFIX}/${PKGMANDIR}/man1

BUILDLINK_API_DEPENDS.pcre2+= pcre2>=10.47
.include "../../devel/pcre2/buildlink3.mk"
.include "../../devel/boost-headers/buildlink3.mk"
.include "../../textproc/tinyxml2/buildlink3.mk"
.include "../../lang/python/application.mk"
.include "../../mk/bsd.pkg.mk"

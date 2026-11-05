# $NetBSD$
# Upstream stable API v2.0; this revision adds separate tool/header roles.
CPPGIR_REV= 0bdd2b6a3cb2b17c36f175b78e914a46784c5b86
DISTNAME= cppgir-${CPPGIR_REV}
PKGNAME= cppgir-2.0.0
PKGREVISION= 2
CATEGORIES= devel
MASTER_SITES= -https://gitlab.com/mnauw/cppgir/-/archive/${CPPGIR_REV}/cppgir-${CPPGIR_REV}.tar.gz
HOMEPAGE= https://gitlab.com/mnauw/cppgir/
COMMENT= C++ binding generator for GObject introspection
LICENSE= mit
USE_LANGUAGES= c c++
CMAKE_CONFIGURE_ARGS+= -DBUILD_TESTING=OFF -DBUILD_DOC=OFF -DBUILD_EXAMPLES=OFF
CMAKE_CONFIGURE_ARGS+= -DINTERNAL_EXPECTED=OFF -DCMAKE_CXX_STANDARD=23
CMAKE_CONFIGURE_ARGS+= -DBUILD_FMT=STDFORMAT
.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# The target package provides headers/config only; target executables never run.
CMAKE_CONFIGURE_ARGS+= -DBUILD_TOOLS=OFF
.else
PLIST.tools= yes
CMAKE_CONFIGURE_ARGS+= -DBUILD_TOOLS=ON
.include "../../devel/boost-headers/buildlink3.mk"
.endif
PLIST_VARS+= tools
INSTALLATION_DIRS+= share/licenses/cppgir
post-install:
	${INSTALL_DATA} ${WRKSRC}/LICENSE ${DESTDIR}${PREFIX}/share/licenses/cppgir/LICENSE
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"

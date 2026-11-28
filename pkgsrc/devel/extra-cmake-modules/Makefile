# $NetBSD: Makefile,v 1.36 2026/09/06 09:43:25 markd Exp $
#
# changelog:
# https://kde.org/announcements/frameworks/6/6.nn.0/

DISTNAME=	extra-cmake-modules-6.32.0
CATEGORIES=	devel kde
MASTER_SITES=	${MASTER_SITE_KDE:=frameworks/${PKGVERSION_NOREV:R}/}
EXTRACT_SUFX=	.tar.xz

MAINTAINER=	markd@NetBSD.org
HOMEPAGE=	https://community.kde.org/Frameworks
COMMENT=	Extra modules and scripts for CMake
LICENSE=	modified-bsd

USE_LANGUAGES=	c++

#TOOLS_DEPEND+=	qt6-qttools-[0-9]*:../../devel/qt6-qttools

CMAKE_CONFIGURE_ARGS+=	-DBUILD_TESTING=OFF
CMAKE_CONFIGURE_ARGS+=	-DBUILD_HTML_DOCS=OFF
CMAKE_CONFIGURE_ARGS+=	-DBUILD_MAN_DOCS=OFF
CMAKE_CONFIGURE_ARGS+=	-DBUILD_QTHELP_DOCS=OFF
# docs/CMakeLists.txt looks for Qt6 ToolsTools even without QtHelp docs. A
# cross Qt in the sysroot then requires QT_HOST_PATH. ECM installs no Qt code.
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_DISABLE_FIND_PACKAGE_Qt6:BOOL=TRUE

CHECK_INTERPRETER_SKIP+=	share/ECM/kde-modules/kde-git-commit-hooks/clang-format.sh
CHECK_INTERPRETER_SKIP+=	share/ECM/kde-modules/kde-git-commit-hooks/json-schema.py
CHECK_INTERPRETER_SKIP+=	share/ECM/kde-modules/kde-git-commit-hooks/pre-commit.in

pre-configure:
	${FIND} ${WRKSRC} -name \*.orig -exec rm {} \;

.include "../../devel/cmake/build.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD" && ${MACHINE_ARCH} == "x86_64"
PKGREVISION=	1	# Reissue: the earlier amd64 name is in a released record.
.endif
.include "../../mk/bsd.pkg.mk"

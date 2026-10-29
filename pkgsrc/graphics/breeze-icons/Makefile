# $NetBSD: Makefile,v 1.65 2026/09/06 10:05:21 markd Exp $

PKGNAME=	${DISTNAME}
PKGREVISION=	2

.include "Makefile.common"

COMMENT=	Breeze icon themes

.include "../../meta-pkgs/kde/kf6.mk"

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# generate-symbolic-dark and qrcAlias run on the build host. A native Ports
# package of the same release provides them in TOOLBASE.
TOOL_DEPENDS+=	breeze-icons-generators-${KF6VER}{,nb[0-9]*}:../../graphics/breeze-icons-generators
CMAKE_CONFIGURE_ARGS+=	-DKF6_HOST_TOOLING=${TOOLBASE:Q}/bin
CMAKE_CONFIGURE_ARGS+=	-DGENERATE_SYMBOLIC_DARK=${TOOLBASE:Q}/bin/generate-symbolic-dark
CMAKE_CONFIGURE_ARGS+=	-DQRC_ALIAS=${TOOLBASE:Q}/bin/qrcAlias
pre-configure: emberbsd-native-breeze-check
.PHONY: emberbsd-native-breeze-check
emberbsd-native-breeze-check:
	${RUN}${TEST} -x ${TOOLBASE:Q}/bin/generate-symbolic-dark && \
	    ${TEST} -x ${TOOLBASE:Q}/bin/qrcAlias || { \
	        echo 'Native Breeze ${KF6VER} generators are required' >&2; exit 1; \
	    }
.endif

PYTHON_FOR_BUILD_ONLY=	tool

.include "../../lang/python/tool.mk"

TOOL_DEPENDS+=	${PYPKGPREFIX}-lxml-[0-9]*:../../textproc/py-lxml

USE_TOOLS+=	bash gsed

LDFLAGS+=	${COMPILER_RPATH_FLAG}${QTDIR}/lib

.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

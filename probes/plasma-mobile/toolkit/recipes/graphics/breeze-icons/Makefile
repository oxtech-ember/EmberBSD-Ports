# $NetBSD: Makefile,v 1.65 2026/09/06 10:05:21 markd Exp $

DISTNAME=	breeze-icons-${KF6VER}
PKGNAME=	${DISTNAME}
PKGREVISION=	1
CATEGORIES=	graphics

HOMEPAGE=	https://community.kde.org/Frameworks
COMMENT=	Breeze icon themes
LICENSE=	gnu-lgpl-v2.1 AND gnu-lgpl-v3

.include "../../meta-pkgs/kde/kf6.mk"

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
.if !defined(EMBERBSD_KF6_BREEZE_HOST) || !defined(EMBERBSD_KF6_HOST_TOOLING)
PKG_FAIL_REASON+= "Set EMBERBSD_KF6_BREEZE_HOST and EMBERBSD_KF6_HOST_TOOLING for cross builds"
.else
CMAKE_CONFIGURE_ARGS+= -DGENERATE_SYMBOLIC_DARK=${EMBERBSD_KF6_BREEZE_HOST:Q}/bin/generate-symbolic-dark
CMAKE_CONFIGURE_ARGS+= -DQRC_ALIAS=${EMBERBSD_KF6_BREEZE_HOST:Q}/bin/qrcAlias
pre-configure: emberbsd-native-breeze-check
.PHONY: emberbsd-native-breeze-check
emberbsd-native-breeze-check:
	${RUN}${TEST} -f ${EMBERBSD_KF6_BREEZE_HOST:Q}/share/ember-breeze-version && \
	    ${TEST} "`${CAT} ${EMBERBSD_KF6_BREEZE_HOST:Q}/share/ember-breeze-version`" = 6.31.0 && \
	    ${TEST} -x ${EMBERBSD_KF6_BREEZE_HOST:Q}/bin/generate-symbolic-dark && \
	    ${TEST} -x ${EMBERBSD_KF6_BREEZE_HOST:Q}/bin/qrcAlias || { \
	        echo 'Matching native Breeze 6.31 generators are required' >&2; exit 1; \
	    }
.endif
.endif


PYTHON_FOR_BUILD_ONLY=	tool

.include "../../lang/python/tool.mk"

TOOL_DEPENDS+=	${PYPKGPREFIX}-lxml-[0-9]*:../../textproc/py-lxml

USE_TOOLS+=	bash gsed

LDFLAGS+=	${COMPILER_RPATH_FLAG}${QTDIR}/lib

.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

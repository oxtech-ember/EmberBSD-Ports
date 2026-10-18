# $NetBSD: Makefile,v 1.3 2026/08/12 03:21:38 ryoon Exp $
# Adapted from x11/tk90. Local changes are AI-assisted.

DISTNAME=	tk${TK_VERSION}-src
PKGNAME=	tk-${TK_VERSION}
CATEGORIES=	x11 lang
MASTER_SITES=	${MASTER_SITE_SOURCEFORGE:=tcl/}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://www.tcl-lang.org/
COMMENT=	Graphical toolkit for Tcl
LICENSE=	2-clause-bsd

.include "Makefile.version"

WRKSRC=			${WRKDIR}/tk${TK_VERSION}
USE_GCC_RUNTIME=	yes
GNU_CONFIGURE=		yes
GNU_CONFIGURE_ICONV=	no
CONFIGURE_DIRS=		unix
BUILD_DIRS=		${CONFIGURE_DIRS}
CONFIGURE_ARGS+=	--with-tcl=${_CROSS_DESTDIR:U}${BUILDLINK_PREFIX.tcl}/lib
CONFIGURE_ARGS+=	--enable-zipfs
CONFIGURE_ENV+=		LIB_RUNTIME_DIR=${PREFIX}/lib
PKGCONFIG_OVERRIDE+=	unix/tk.pc.in
USE_TOOLS+=		gmake ln pkg-config
TOOL_DEPENDS+=		zip-[0-9]*:../../archivers/zip
TEST_TARGET=		test
CHECK_PORTABILITY_SKIP=	win/configure

.include "options.mk"

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# The embedded script archive and host helper must use native tools.
TOOL_DEPENDS+=		tcl>=${TCL_VERSION}:../../lang/tcl
CONFIGURE_ENV+=		CC_FOR_BUILD=${NATIVE_CC:Q}
CONFIGURE_ENV+=		ac_cv_path_tclsh=${TOOLBASE}/bin/tclsh
CONFIGURE_ENV+=		EMBERBSD_TCL_SYSTEM_NAME=${OPSYS:Q}
CONFIGURE_ENV+=		EMBERBSD_TCL_SYSTEM_RELEASE=${OS_VERSION:Q}
.endif

SUBST_CLASSES+=		tk-config
SUBST_STAGE.tk-config=	post-build
SUBST_FILES.tk-config=	unix/tkConfig.sh
SUBST_SED.tk-config+=	-e "s|${WRKSRC}/unix|${PREFIX}/lib|"
SUBST_SED.tk-config+=	-e "s|${WRKSRC}|${PREFIX}/include/tk|"

PLIST_SUBST+=		SONUM=${TK_SONUM}
PLIST_SUBST+=		BASEVER=${TK_BASEVER}
PLIST_SUBST+=		VERSION=${TK_VERSION}

post-install:
	cd ${WRKSRC}/unix && ${MAKE} \
		BIN_INSTALL_DIR=${DESTDIR}${PREFIX}/bin \
		LIB_INSTALL_DIR=${DESTDIR}${PREFIX}/lib \
		CONFIG_INSTALL_DIR=${DESTDIR}${PREFIX}/lib \
		SCRIPT_INSTALL_DIR=${DESTDIR}${PREFIX}/lib/tk${TK_BASEVER} \
		INCLUDE_INSTALL_DIR=${DESTDIR}${PREFIX}/include \
		PRIVATE_INCLUDE_INSTALL_DIR=${DESTDIR}${PREFIX}/include \
		MAN_INSTALL_DIR=${DESTDIR}${PREFIX}/${PKGMANDIR} \
		DEMO_INSTALL_DIR=${DESTDIR}${PREFIX}/lib/tk${TK_BASEVER}/demos \
		install-binaries install-libraries install-headers \
		install-private-headers install-demos
	cd ${DESTDIR}${PREFIX}/bin && ${LN} -fs wish${TK_BASEVER} wish

.include "../../lang/tcl/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

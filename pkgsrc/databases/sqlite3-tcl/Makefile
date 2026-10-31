# $NetBSD: Makefile,v 1.130 2026/01/10 17:04:27 adam Exp $

.include "../../databases/sqlite3/Makefile.common"

DISTNAME=	sqlite-autoconf-${SQLITE3_DISTVERSION}
PKGNAME=	sqlite3-tcl-${SQLITE3_VERSION}
CATEGORIES=	databases

MAINTAINER=	pkgsrc-users@NetBSD.org
COMMENT=	SQL Database Engine in a C Library (TCL extension)

WRKSRC=		${WRKDIR}/${DISTNAME}/tea

USE_TOOLS+=		gmake
HAS_CONFIGURE=		yes
# tclConfig.sh is read at configure time: in a cross build it is in the
# target root, not at the logical prefix on the build host.
CONFIGURE_ARGS+=	--with-tcl=${_CROSS_DESTDIR:U}${BUILDLINK_PREFIX.tcl}/lib
# Link the one common provider, not the bundled SQLite amalgamation.
CONFIGURE_ARGS+=	--with-system-sqlite
CONFIGURE_ARGS+=	--override-sqlite-version=${SQLITE3_VERSION}
CONFIGURE_ENV+=		TCLLIBDIR=${PREFIX}/lib/tcl${TCL_BASEVER}/sqlite${SQLITE3_VERSION}
LDFLAGS+=		${COMPILER_RPATH_FLAG}${BUILDLINK_PREFIX.sqlite3}/lib
INSTALL_TARGET=		install-core

PLIST_SUBST+=		TCL_BASEVER=${TCL_BASEVER}

BUILDLINK_API_DEPENDS.sqlite3+=	sqlite3>=3.54.1

.include "../../mk/bsd.prefs.mk"

.include "../../databases/sqlite3/cross.mk"

.if ${OPSYS} == "Darwin"
post-install:
	''${EMBERBSD_DARWIN_INSTALL_NAME_TOOL:Uinstall_name_tool:Q} -id \
	    ${PREFIX}/lib/tcl${TCL_BASEVER}/sqlite${PKGVERSION_NOREV}/libtcl9sqlite${PKGVERSION_NOREV}.dylib \
	    ${DESTDIR}${PREFIX}/lib/tcl${TCL_BASEVER}/sqlite${PKGVERSION_NOREV}/libtcl9sqlite${PKGVERSION_NOREV}.dylib
.endif

.include "../../databases/sqlite3/buildlink3.mk"
.include "../../lang/tcl/buildlink3.mk"
.include "../../mk/readline.buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

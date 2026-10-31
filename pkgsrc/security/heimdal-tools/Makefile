# $NetBSD$

DISTNAME=	heimdal-7.8.0
PKGNAME=	${DISTNAME:S/heimdal/heimdal-tools/}
CATEGORIES=	security
MASTER_SITES=	${MASTER_SITE_GITHUB:=heimdal/}
GITHUB_RELEASE=	${DISTNAME}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	http://www.h5l.org/
COMMENT=	Heimdal code generators for cross builds of Heimdal
LICENSE=	modified-bsd

# Same source and patch set as security/heimdal, so the generators match the
# library sources they produce code for.
DISTINFO_FILE=	${.CURDIR}/../../security/heimdal/distinfo
PATCHDIR=	${.CURDIR}/../../security/heimdal/patches

USE_TOOLS+=		bison flex perl
GNU_CONFIGURE=		yes
GNU_CONFIGURE_STRICT=	no # has multiple configure scripts
# Static helper libraries with the bundled libtool (pkgsrc libtool would
# build them shared anyway): the generators need no Heimdal libraries at run
# time, and the package installs no libraries or headers, so it does not
# conflict with security/mit-krb5 or security/heimdal in a tool prefix.
CONFIGURE_ARGS+=	--disable-shared --enable-static
CONFIGURE_ARGS+=	--without-openssl --without-x --without-readline
CONFIGURE_ARGS+=	--without-libedit --without-sqlite3 --without-berkeley-db
CONFIGURE_ARGS+=	--disable-otp --disable-pk-init --disable-digest
CONFIGURE_ARGS+=	--disable-kx509 --disable-ndbm-db --disable-mdb-db
CONFIGURE_ARGS+=	--disable-afs-support --disable-sqlite-cache
CONFIGURE_ARGS+=	--disable-heimdal-documentation
CONFIGURE_ENV+=		COMPILE_ET=no	# build Heimdal's compile_et(1)
# configure requires a Python interpreter; the generators do not use it.
PYTHON_FOR_BUILD_ONLY=	tool
CONFIGURE_ENV+=		PYTHON=${PYTHONBIN}

.include "../../mk/bsd.prefs.mk"

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
PKG_FAIL_REASON+=	"${PKGNAME} provides build-host tools; use it from TOOL_DEPENDS"
.endif

INSTALLATION_DIRS=	libexec/heimdal-tools

# Build only what asn1_compile, slc and compile_et need.  slc uses no libsl
# function, so link it without libsl and the line editor libsl pulls in.
do-build:
.for d in include lib/roken lib/vers
	cd ${WRKSRC}/${d} && ${BUILD_MAKE_CMD}
.endfor
	cd ${WRKSRC}/lib/com_err && ${BUILD_MAKE_CMD} compile_et
	cd ${WRKSRC}/lib/sl && \
	    ${BUILD_MAKE_CMD} slc LDADD='$$(LIB_roken)' slc_DEPENDENCIES=
	cd ${WRKSRC}/lib/asn1 && ${BUILD_MAKE_CMD} asn1_compile

do-install:
.for t in lib/com_err/compile_et lib/sl/slc lib/asn1/asn1_compile
	${INSTALL_PROGRAM} ${WRKSRC}/${t} \
	    ${DESTDIR}${PREFIX}/libexec/heimdal-tools/${t:T}
.endfor

.include "../../lang/python/pyversion.mk"
.include "../../mk/bsd.pkg.mk"

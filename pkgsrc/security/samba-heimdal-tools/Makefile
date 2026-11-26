# $NetBSD$

.include "../../net/samba4/Makefile.version"

DISTNAME=	samba-${SAMBA_VERSION}
PKGNAME=	samba-heimdal-tools-${SAMBA_VERSION}
CATEGORIES=	security devel
MASTER_SITES=	https://download.samba.org/pub/samba/stable/

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://www.samba.org/
COMMENT=	Lorikeet Heimdal code generators for Samba
LICENSE=	modified-bsd

PATCH_STRIP=		-p2
EXTRACT_ELEMENTS=	${DISTNAME}/third_party/heimdal
WRKSRC=			${WRKDIR}/${DISTNAME}/third_party/heimdal
USE_TOOLS+=		autoconf automake autoreconf bison flex gmake libtoolize perl pkg-config
GNU_CONFIGURE=		yes
GNU_CONFIGURE_STRICT=	no
CONFIGURE_ARGS+=	--disable-shared --enable-static
CONFIGURE_ARGS+=	--without-openssl --without-x --without-readline
CONFIGURE_ARGS+=	--without-libedit --without-sqlite3 --without-berkeley-db
CONFIGURE_ARGS+=	--disable-otp --disable-pk-init --disable-digest
CONFIGURE_ARGS+=	--disable-kx509 --disable-ndbm-db --disable-mdb-db
CONFIGURE_ARGS+=	--disable-afs-support --disable-heimdal-documentation
CONFIGURE_ENV+=		COMPILE_ET=no PYTHON=${PYTHONBIN}
PYTHON_FOR_BUILD_ONLY=	tool

.include "../../mk/bsd.prefs.mk"

.if ${OPSYS} == "Darwin"
# The generated lexers use POSIX interfaces and Darwin resolver types.
CPPFLAGS+=	-D_DARWIN_C_SOURCE
PKGREVISION=	1
.endif

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
PKG_FAIL_REASON+=	"${PKGNAME} provides build-host generators"
.endif

INSTALLATION_DIRS=	libexec/samba-heimdal-tools

pre-configure:
	cd ${WRKSRC} && ${SETENV} ${MAKE_ENV} autoreconf -fi

do-build:
.for d in include lib/roken lib/vers
	cd ${WRKSRC}/${d} && ${BUILD_MAKE_CMD}
.endfor
	cd ${WRKSRC}/lib/com_err && ${BUILD_MAKE_CMD} compile_et
	cd ${WRKSRC}/lib/base && ${BUILD_MAKE_CMD} heim_err.h heimbase-protos.h
	cd ${WRKSRC}/lib/asn1 && ${BUILD_MAKE_CMD} asn1_compile

do-install:
.for t in lib/com_err/compile_et lib/asn1/asn1_compile
	${INSTALL_PROGRAM} ${WRKSRC}/${t} ${DESTDIR}${PREFIX}/libexec/samba-heimdal-tools/${t:T}
.endfor

.include "../../lang/python/pyversion.mk"
.include "../../mk/bsd.pkg.mk"

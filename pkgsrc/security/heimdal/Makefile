# $NetBSD: Makefile,v 1.172 2026/01/07 08:48:40 wiz Exp $

DISTNAME=	heimdal-7.8.0
PKGREVISION=	30
CATEGORIES=	security
MASTER_SITES=	${MASTER_SITE_GITHUB:=heimdal/}
GITHUB_RELEASE=	${DISTNAME}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	http://www.h5l.org/
COMMENT=	Kerberos 5 implementation
LICENSE=	modified-bsd

TOOL_DEPENDS+=	p5-JSON-[0-9]*:../../converters/p5-JSON

CONFLICTS+=	arla-[0-9]*
CONFLICTS+=	mit-krb5-[0-9]*
CONFLICTS+=	gss-[0-9]*
CONFLICTS+=	kth-krb4-[0-9]*

USE_LIBTOOL=		yes
USE_TOOLS+=		bison flex:run perl pkg-config
PKGCONFIG_OVERRIDE+=	tools/heimdal-gssapi.pc.in
MAKE_ENV+=		INSTALL_CATPAGES=no

.include "../../mk/bsd.prefs.mk"

# Select the native Ports MIG producer and compiler for Darwin IPC sources.
.if ${USE_CROSS_COMPILE:Uno:tl} == "no" && ${OPSYS} == "Darwin"
CURSES_DEFAULT= ncurses
PREFER.ncurses= pkgsrc
BUILD_DEPENDS+= mig>=138:../../devel/mig
MAKE_FLAGS+= MIG=${TOOLBASE:Q}/bin/mig LIBTOOL=${LIBTOOL:Q}\ --tag=CC
MAKE_ENV+= MIGCC=${CC:Q} MIGCOM=${TOOLBASE:Q}/libexec/migcom
.if !empty(OSX_SDK_PATH)
MAKE_ENV+= SDKROOT=${OSX_SDK_PATH:Q}
.endif
.endif

BUILD_DEFS+=		VARBASE

.include "options.mk"

HEIMDAL_HDB_DIR=	${VARBASE}/heimdal

GNU_CONFIGURE=		yes
GNU_CONFIGURE_STRICT=	no # has multiple configure scripts
CONFIGURE_ARGS+=	--enable-kcm
CONFIGURE_ARGS+=	--enable-pthread-support
CONFIGURE_ARGS+=	--includedir=${PREFIX}/include/krb5
CONFIGURE_ARGS+=	--sysconfdir=${PKG_SYSCONFDIR}
CONFIGURE_ARGS+=	--with-hdbdir=${HEIMDAL_HDB_DIR}
# Resolve target readline against the physical buildlink tree on a cross host.
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
READLINE_DEFAULT= readline
PREFER.readline= pkgsrc
PREFER.openssl= pkgsrc
CONFIGURE_ARGS+= --with-openssl=${BUILDLINK_DIR}
CONFIGURE_ARGS+= --with-readline=${BUILDLINK_DIR}
.else
CONFIGURE_ARGS+= --with-readline=${BUILDLINK_PREFIX.editlinereadline}
.endif
# The target prefix is logical on a cross host; configure tests host paths.
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
CONFIGURE_ARGS+= --with-sqlite3=${BUILDLINK_DIR}
.else
CONFIGURE_ARGS+= --with-sqlite3=${BUILDLINK_PREFIX.sqlite3}
.endif
CONFIGURE_ARGS+=	--without-x
CONFIGURE_ARGS+=	${ABI:D--with-mips-abi=${ABI}}
CONFIGURE_ENV+=		COMPILE_ET=no	# build Heimdal's compile_et(1)
CONFIGURE_ENV+=		PYTHON=${PYTHONBIN}

CFLAGS+=		-Wno-error=implicit-function-declaration

.include "../../mk/bdb.buildlink3.mk"

# XXX Don't detect db1 when a newer version is available; otherwise build fails
.if ${BDB_TYPE} != "db1"
CONFIGURE_ENV+=		ac_cv_funclib_dbopen=no
.endif

CFLAGS.Darwin+=		-DBIND_8_COMPAT

# Newer illumos has extended functions in glob(3C) but it's easier to
# say it doesn't for simpler PLIST.glob handling.
CONFIGURE_ENV.SunOS+=	ac_cv_func_glob_working=no

# Though Solaris has a <vis.h> header, it does something very unrelated
# to the BSD <vis.h> header.
CONFIGURE_ENV.SunOS+=	ac_cv_header_vis_h=no

PLIST_VARS+=		glob vis afskauth native_tools
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# security/heimdal-tools installs only the native code generators into the
# tool prefix; they are not a build-host path setting.  The full native
# Heimdal would conflict with MIT Kerberos that other native tools pull in.
# The tools exist only after the depends step: check them before configure,
# not at parse time (fetch).
TOOL_DEPENDS+= heimdal-tools>=7.8.0:../../security/heimdal-tools
_EMBERBSD_HEIMDAL_TOOLS_DIR= ${TOOLBASE}/libexec/heimdal-tools
.  if empty(_EMBERBSD_HEIMDAL_TOOLS_DIR:M${TOOLBASE}/*)
PKG_FAIL_REASON+= Select\ the\ native\ Heimdal\ cross-tools\ directory
.  endif
CONFIGURE_ARGS+= --with-cross-tools=${_EMBERBSD_HEIMDAL_TOOLS_DIR:Q}
.else
PLIST.native_tools= yes
post-install:
	${LIBTOOL} --mode=install ${INSTALL_PROGRAM} ${WRKSRC}/lib/com_err/compile_et ${DESTDIR}${PREFIX}/libexec/heimdal/compile_et
.endif

.if ${OPSYS} == "SunOS"
PLIST.vis=	yes
PLIST.glob=	yes
.endif

.if ${OPSYS} == "IRIX"
PLIST.afskauth=		yes
.endif

OWN_DIRS_PERMS=		${HEIMDAL_HDB_DIR} ${REAL_ROOT_USER} ${REAL_ROOT_GROUP} 0700
SPECIAL_PERMS+=		${PREFIX}/bin/otp ${SETUID_ROOT_PERMS}
SPECIAL_PERMS+=		${PREFIX}/bin/${KRB5_PREFIX}su ${SETUID_ROOT_PERMS}
RCD_SCRIPTS=		kadmind kcm kdc kpasswdd
INFO_FILES=		yes

TEST_TARGET=		check

# remove manpages conficting with OpenSSL keeping only the important ones
post-extract:
	${CP} ${FILESDIR}/heim_find_prime.h ${WRKSRC}/lib/hcrypto/heim_find_prime.h

pre-configure:
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
	${TEST} -f ${BUILDLINK_DIR}/lib/libcrypto.so || \
	    { ${ECHO} "Selected OpenSSL is missing from the buildlink tree"; exit 1; }
	for t in asn1_compile slc compile_et; do \
		${TEST} -x ${_EMBERBSD_HEIMDAL_TOOLS_DIR:Q}/$$t || \
		{ ${ECHO} "Native Heimdal tool $$t is missing"; exit 1; }; \
	done
.endif
	cd ${WRKSRC}/doc/doxyout/hcrypto && \
	${GREP} -e /hcrypto_ -e /page_ manpages > manpages.new && \
	mv manpages.new manpages

.include "../../math/libtommath/buildlink3.mk"
.include "../../databases/sqlite3/buildlink3.mk"

# Linux does not have include/vis.h and expected include/glob.h.
.if ${OPSYS} == "Linux"
PLIST.vis=		yes
PLIST.glob=		yes
# Without this I get undefined references to pthread_getspecific
PTHREAD_AUTO_VARS=	yes
.endif

.if ${OPSYS} == "Minix"
# all of the tools need to link against pthread, force it.
PTHREAD_AUTO_VARS=	yes
.endif

.include "../../lang/python/pyversion.mk"
.include "../../security/openssl/buildlink3.mk"
# integrated editline configure script that always runs checks for this
.include "../../mk/curses.buildlink3.mk"
.include "../../mk/pthread.buildlink3.mk"
.include "../../mk/readline.buildlink3.mk"
.include "../../mk/termcap.buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

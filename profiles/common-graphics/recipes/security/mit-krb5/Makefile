# $NetBSD: Makefile,v 1.124 2026/04/07 14:12:48 tnn Exp $

EMBERBSD_MIT_KRB5_PKGDIR:= ${.PARSEDIR:tA}

BRANCHNAME=	1.22
DISTNAME=	krb5-${BRANCHNAME}.2
PKGNAME=	mit-${DISTNAME}
PKGREVISION=	5
CATEGORIES=	security
# It is not clear how stable this URL scheme is.
MASTER_SITES=	http://web.mit.edu/kerberos/dist/krb5/${BRANCHNAME}/

MAINTAINER=	tez@NetBSD.org
HOMEPAGE=	https://web.mit.edu/kerberos/
COMMENT=	MIT Kerberos 5 authentication system

# There is a file NOTICE in the sources, which is enormous.  Most
# licenses appear to be some flavor of X11, 3-clause BSD, 4-clause
# BSD.
# 20201007: gdt emailed upstream asking for clarification on the AES
# license, which is not entirely clearly Free, by the text.
#LICENSE=

# TODO: This is entirely caused by our libtool patches, which are also
# actively harmful when trying to run the test suite.  They should really
# be completely deleted and we instead homogenise shared objects to have
# the same naming across all platforms.
MAKE_JOBS_SAFE=	no

WRKSRC=		${WRKDIR}/${DISTNAME}/src

BUILD_TARGET=	generate-files-mac all

.include "../../mk/bsd.prefs.mk"

CONFLICTS+=	heimdal-[0-9]*
CONFLICTS+=	kth-krb4-[0-9]*

USE_LANGUAGES=		c
# Upstream does not document the language variant.  It appears to be
# c99, and configure checks for that.  The code uses strdup(3):
# https://pubs.opengroup.org/onlinepubs/9799919799/functions/strdup.html
# and that's hidden by default on Linux, with gnu99 making it visible.
USE_CC_FEATURES+=	c99
FORCE_C_STD=		gnu99

USE_LIBTOOL=		yes
GNU_CONFIGURE=		yes
USE_TOOLS+=		autoconf bison gzip m4 msgfmt perl

# The actual KDC databases are stored in ${MIT_KRB5_STATEDIR}/krb5kdc.
MIT_KRB5_STATEDIR?=	${VARBASE}
FILES_SUBST+=		MIT_KRB5_STATEDIR=${MIT_KRB5_STATEDIR}

BUILD_DEFS+=		VARBASE

# Keep the upstream thread-safe client library for GUI consumers.
CONFIGURE_ARGS+=	--enable-thread-support

# Resolve compiler flags before Autoconf creates installed metadata.
SUBST_CLASSES+=		krb5-rpath
SUBST_STAGE.krb5-rpath=	pre-configure
SUBST_FILES.krb5-rpath=	config/shlib.conf
SUBST_VARS.krb5-rpath=	COMPILER_RPATH_FLAG

CONFIGURE_ARGS+=	--localstatedir=${MIT_KRB5_STATEDIR}
CONFIGURE_ARGS+=	--sysconfdir=${PKG_SYSCONFDIR}
CONFIGURE_ARGS+=	--disable-aesni
CONFIGURE_ARGS+=	--disable-kdc-lookaside-cache
CONFIGURE_ARGS+=	--enable-shared
CONFIGURE_ARGS+=	--enable-dns-for-realm
CONFIGURE_ARGS+=	--enable-pkgsrc-libtool
CONFIGURE_ARGS+=	--without-system-verto
CONFIGURE_ENV+=		BUILDLINK_PREFIX_OPENSSL=${BUILDLINK_PREFIX.openssl}
CONFIGURE_ENV+=		DEFKTNAME=FILE:${PKG_SYSCONFDIR}/krb5.keytab
.if ${USE_CROSS_COMPILE:Uno} == "yes"
# Build-time compile_et keeps host tools. The installed script uses target tools.
MAKE_FLAGS+=		INSTALL_AWK=/usr/bin/awk INSTALL_SED=/usr/bin/sed
.endif
MAKE_ENV+=		ROOT_USER=${ROOT_USER}
MAKE_ENV+=		YFLAGS="-Wnone"
.if ${USE_CROSS_COMPILE:Uno:tl} == "no" && ${OPSYS} == "Darwin"
# The native C compiler can differ from the libtool default command.
MAKE_FLAGS+=		LIBTOOL=${LIBTOOL:Q}\ --tag=CC
.if !empty(OSX_SDK_PATH)
# Darwin MIG reads SDKROOT when it selects its preprocessor headers.
MAKE_ENV+=		SDKROOT=${OSX_SDK_PATH:Q}
.endif
.endif
LIBS.SunOS=		-lrt

OWN_DIRS_PERMS=		${MIT_KRB5_STATEDIR}/krb5kdc			\
			${REAL_ROOT_USER} ${REAL_ROOT_GROUP} 0700
RCD_SCRIPTS=		kadmind kdc

.if defined(EMBERBSD_MIT_KRB5_DEVEL)
.if ${EMBERBSD_MIT_KRB5_DEVEL} != "yes" || ${PKGPATH} != "security/mit-krb5-devel"
PKG_FAIL_REASON+= "The MIT Kerberos SDK role belongs to security/mit-krb5-devel"
.endif
PKGNAME= mit-krb5-devel-${BRANCHNAME}.2
COMMENT= MIT Kerberos target SDK for the development-host sysroot
DISTINFO_FILE= ${EMBERBSD_MIT_KRB5_PKGDIR}/distinfo
PATCHDIR= ${EMBERBSD_MIT_KRB5_PKGDIR}/patches
FILESDIR= ${EMBERBSD_MIT_KRB5_PKGDIR}/files
RCD_SCRIPTS=
OWN_DIRS_PERMS=
DEPENDS+= mit-krb5>=${BRANCHNAME}.2nb2:../../security/mit-krb5
CONFLICTS+= mit-krb5<${BRANCHNAME}.2nb2
.if ${USE_CROSS_COMPILE:Uno:tl} != "yes" || ${OPSYS} != "NetBSD"
PKG_FAIL_REASON+= "The MIT Kerberos SDK requires a NetBSD cross build; native builds keep the full package"
.endif
.endif

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD"
.if ${MACHINE_ARCH} != "aarch64" && ${MACHINE_ARCH} != "x86_64"
PKG_FAIL_REASON+= "The MIT Kerberos split requires a common AArch64 or amd64 target"
.endif
LIBTOOLIZE_PLIST= no
MIT_KRB5_FULL_PLIST= ${EMBERBSD_MIT_KRB5_PKGDIR}/PLIST.full-cross
MIT_KRB5_RUNTIME_PLIST= ${EMBERBSD_MIT_KRB5_PKGDIR}/PLIST.runtime
MIT_KRB5_DEVEL_PLIST= ${EMBERBSD_MIT_KRB5_PKGDIR}/../mit-krb5-devel/PLIST
.if defined(EMBERBSD_MIT_KRB5_DEVEL)
MIT_KRB5_PACKAGE_PART= devel
PLIST_SRC= ${MIT_KRB5_DEVEL_PLIST}
.else
MIT_KRB5_PACKAGE_PART= runtime
PLIST_SRC= ${MIT_KRB5_RUNTIME_PLIST}
.endif
.if !defined(EMBERBSD_SDK_SOURCE) || !defined(EMBERBSD_CROSS_BUILD_PYTHON)
PKG_FAIL_REASON+= "MIT Kerberos cross packages require EMBERBSD_SDK_SOURCE and EMBERBSD_CROSS_BUILD_PYTHON"
.endif
.endif

INSTALLATION_DIRS=	bin include/gssapi include/gssrpc ${PKGINFODIR}	\
			${PKGMANDIR}/man1 ${PKGMANDIR}/man5		\
			${PKGMANDIR}/man7 ${PKGMANDIR}/man8		\
			sbin share/examples/krb5 share/et		\
			share/examples/rc.d share/gnats			\
			lib/krb5/plugins/kdb lib/krb5/plugins/preauth	\
			lib/krb5/plugins/tls include/krb5 include/kadm5 \
			lib/pkgconfig

.include "../../mk/compiler.mk"

.include "options.mk"

pre-configure:
	cd ${WRKSRC} && autoconf -I ${WRKSRC} -f

.include "../../databases/lmdb/buildlink3.mk"
.include "../../security/openssl/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD"
post-install: mit-krb5-select-stage
.PHONY: mit-krb5-select-stage
mit-krb5-select-stage: install-rcd-scripts
.for _mit_part in FULL RUNTIME DEVEL
	${MAKE} ${WRKDIR:Q}/.mit-krb5-${_mit_part:tl}-plist \
	    PLIST=${WRKDIR:Q}/.mit-krb5-${_mit_part:tl}-plist \
	    PLIST_SRC=${MIT_KRB5_${_mit_part}_PLIST:Q} RCD_SCRIPTS=
.endfor
	${EMBERBSD_CROSS_BUILD_PYTHON} ${FILESDIR}/select-stage.py \
	    --sdk-source ${EMBERBSD_SDK_SOURCE:Q} ${MIT_KRB5_PACKAGE_PART:Q} \
	    ${DESTDIR:Q}${PREFIX:Q} ${WRKDIR:Q}/.mit-krb5-full-plist \
	    ${WRKDIR:Q}/.mit-krb5-runtime-plist ${WRKDIR:Q}/.mit-krb5-devel-plist
.endif

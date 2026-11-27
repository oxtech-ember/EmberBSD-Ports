# $NetBSD: Makefile,v 1.65 2026/08/03 12:32:11 wiz Exp $
#
# Please also update the dependency pattern in mozilla-rootcerts-openssl
# and bump its version when updating this package.

DISTNAME=	mozilla-rootcerts-1.1.${CERTDATA_DATE}
PKGREVISION=	1
CATEGORIES=	security
# The NSS release tag is reachable; the GitHub mirror lacks the commit.
MASTER_SITES=	-https://hg.mozilla.org/projects/nss/raw-file/${CERTDATA_NSS_TAG}/lib/ckfw/builtins/certdata.txt
MASTER_SITES+=	-https://raw.githubusercontent.com/nss-dev/nss/${CERTDATA_COMMIT}/lib/ckfw/builtins/certdata.txt
EXTRACT_SUFX=	# empty
DISTFILES=	${CERTDATA}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://hg.mozilla.org/mozilla-central/log/tip/security/nss/lib/ckfw/builtins/certdata.txt
COMMENT=	Root CA certificates from the Mozilla Project
LICENSE=	mpl-2.0

USE_TOOLS=	awk:run echo:run expr:run ln:run ls:run openssl:run rm:run mkdir:run

# This must be kept in sync with security/mozilla-rootcerts-openssl
# https://hg-edge.mozilla.org/mozilla-central/log/tip/security/nss/lib/ckfw/builtins/certdata.txt
# 'created' date
# NSS 3.134 release includes this certdata revision.
CERTDATA_DATE=		20261113
# 'git commit hash'
CERTDATA_COMMIT=	8c60e757c30b1b239bae46532b4f6d4ebb1e1cad
CERTDATA_NSS_TAG=	NSS_3_134_RTM
CERTDATA=		certdata-${CERTDATA_DATE}.txt

WRKSRC=		${WRKDIR}
DATADIR=	${PREFIX}/share/${PKGBASE}

# Set paths depending on whether we depend on builtin or pkgsrc
# openssl.  \todo Arguably, we should consider installing into both
# builtin and pkgsrc, if both exist, but this requires much more
# thought.
CHECK_BUILTIN.openssl=	yes
.include "../../security/openssl/builtin.mk"
CHECK_BUILTIN.openssl=	no
.if ${USE_BUILTIN.openssl:U:tl} == yes
SSLDIR=		/etc/openssl
.else
SSLDIR=		${PKG_SYSCONFDIR}/openssl
.endif

CERT_SCRIPT=		mozilla-rootcerts.sh

SUBST_CLASSES=		paths
SUBST_MESSAGE.paths=	Replacing hard-coded paths.
SUBST_STAGE.paths=	post-configure
SUBST_FILES.paths=	${CERT_SCRIPT}
SUBST_VARS.paths=	AWK DATADIR ECHO EXPR LN LS MKDIR PREFIX RM SH SSLDIR
SUBST_SED.paths=	-e 's,@OPENSSL@,${TOOLS_PATH.openssl},g'

INSTALLATION_DIRS=	sbin ${DATADIR} share/doc/${PKGBASE}

do-extract:
	${CP} ${FILESDIR}/${CERT_SCRIPT} ${WRKSRC}
	${CP} ${DISTDIR}/${CERTDATA} ${WRKSRC}/certdata.txt

do-build:
	${MKDIR} ${WRKSRC}/certs
	cd ${WRKSRC}/certs && \
	${SH} ${WRKSRC}/${CERT_SCRIPT} -f ${WRKSRC}/certdata.txt extract
	${LS} -rt ${WRKSRC}/certs/*.pem | ${XARGS} ${CAT} >${WRKSRC}/cacert.pem

do-install:
	${INSTALL_SCRIPT} ${WRKSRC}/${CERT_SCRIPT} \
		${DESTDIR}${PREFIX}/sbin/mozilla-rootcerts
	${INSTALL_DATA} ${WRKSRC}/certdata.txt ${DESTDIR}${DATADIR}/certdata.txt
	${INSTALL_DATA} ${FILESDIR}/retired-tls-sha256 ${DESTDIR}${DATADIR}/retired-tls-sha256
	${INSTALL_DATA} ${WRKSRC}/cacert.pem ${DESTDIR}${DATADIR}/cacert.pem
	${INSTALL_DATA} files/gnupg2 ${DESTDIR}${PREFIX}/share/doc/${PKGBASE}

.include "../../mk/bsd.pkg.mk"

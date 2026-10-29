# $NetBSD: Makefile,v 1.110 2025/05/17 19:20:44 zafer Exp $
#

DISTNAME=	ntp-4.2.8p18
CATEGORIES=	net time
MASTER_SITES=	https://downloads.nwtime.org/ntp/4.2.8/

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	http://www.ntp.org/
COMMENT=	Network Time Protocol Version 4

CONFLICTS+=	openntpd-[0-9]*

GNU_CONFIGURE=	YES
USE_LIBTOOL=	YES
USE_TOOLS+=	pax perl:run pkg-config
PYTHON_FOR_BUILD_ONLY=	tool
REPLACE_SH+=		sntp/scripts/genLocInfo sntp/scripts/cvo.sh

CONFIGURE_ARGS+=	--sysconfdir=${PKG_SYSCONFDIR}
CONFIGURE_ARGS+=	--with-locfile=loc/pkgsrc
CONFIGURE_ENV+=		PATH_PERL=${PERL5}
CONFIGURE_ARGS+=	--disable-local-libevent
CONFIGURE_ENV+=		EMBER_NTP_EXTERNAL_LIBEVENT=yes

OVERRIDE_DIRDEPTH=	4

DOCS+=		COPYRIGHT ChangeLog NEWS README* TODO
DOCDIR=		share/doc/ntp
EXAMPLESDIR=	share/examples/ntp4
ALL_NTP_DOCS=	${DESTDIR}${PREFIX}/${DOCDIR} ${DESTDIR}${PREFIX}/${EXAMPLESDIR}

INSTALLATION_DIRS=	${DOCDIR} ${EXAMPLESDIR}

RCD_SCRIPTS=	ntpd ntpdate

post-install:
	${RM} -f ${DESTDIR}${PREFIX}/${DOCDIR}/html/.datecheck
	cd ${WRKSRC} && ${INSTALL_DATA} ${DOCS} ${DESTDIR}${PREFIX}/${DOCDIR}
	cd ${WRKSRC}/conf && pax -rw -pm . ${DESTDIR}${PREFIX}/${EXAMPLESDIR}
	${CHOWN} -R ${SHAREOWN}:${SHAREGRP} ${ALL_NTP_DOCS}
	${FIND} ${ALL_NTP_DOCS} -type d -print | ${XARGS} ${CHMOD} ${PKGDIRMODE}
	${FIND} ${ALL_NTP_DOCS} -type f -print | ${XARGS} ${CHMOD} ${SHAREMODE}

.include "../../mk/bsd.prefs.mk"
.include "options.mk"

.if empty(EMBER_NTP_LIBOPTS_SOURCE:M/*) || !exists(${EMBER_NTP_LIBOPTS_SOURCE}/emberbsd-prepared-source.json)
PKG_FAIL_REASON+= "Set EMBER_NTP_LIBOPTS_SOURCE to prepared common AutoGen libopts source"
.endif
.if empty(EMBERBSD_SDK_SOURCE:M/*) || !exists(${EMBERBSD_SDK_SOURCE}/src/emberbsd_sdk/sourceprep.py)
PKG_FAIL_REASON+= "Set EMBERBSD_SDK_SOURCE to the selected SDK source"
.endif

post-patch: ember-ntp-libopts
.PHONY: ember-ntp-libopts
ember-ntp-libopts:
	${RUN}${TOOL_PYTHONBIN:Q} -B ${FILESDIR}/install-libopts-source.py \
	    --sdk-source ${EMBERBSD_SDK_SOURCE:Q} --pkgsrc ${_PKGSRCDIR:Q} \
	    --source ${EMBER_NTP_LIBOPTS_SOURCE:Q} --ntp ${WRKSRC:Q}

# Configure enables these utilities according to the actual target capabilities.
GENERATE_PLIST+= ${TOOL_PYTHONBIN:Q} -B ${FILESDIR}/plist-features.py ${WRKSRC:Q}/config.status;

# chroot jail support
.if ${OPSYS} == "NetBSD"
CONFIGURE_ARGS+=	--enable-clockctl
.elif ${OPSYS} == "Linux" && exists(/usr/include/sys/capability.h)
CONFIGURE_ARGS+=	--enable-linuxcaps
.else
# no chroot/privilege drop supported
.endif

CPPFLAGS.Linux+=	-D_GNU_SOURCE	# for struct in6_pktinfo

.include "../../devel/libevent/buildlink3.mk"
.include "../../lang/python/tool.mk"
.include "../../security/openssl/buildlink3.mk"

CONFIGURE_ARGS+=	--with-openssl-incdir=${BUILDLINK_DIR}/include
CONFIGURE_ARGS+=	--with-openssl-libdir=${BUILDLINK_DIR}/lib
CONFIGURE_ARGS+=	--with-crypto=openssl

.include "../../mk/readline.buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

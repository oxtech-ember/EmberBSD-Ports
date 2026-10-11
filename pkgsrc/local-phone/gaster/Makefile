# EmberBSD: checkm8 PwnedDFU helper for Apple A5-A11 devices (phone rescue kit).
DISTNAME=	gaster-20230202
PKGNAME=	gaster-20230202
CATEGORIES=	comms
MASTER_SITES=	${MASTER_SITE_GITHUB:=0x7ff/}
GITHUB_PROJECT=	gaster
GITHUB_TAG=	7fffffff38a1bed1cdc1c5bae0df70f14395129b
WRKSRC=		${WRKDIR}/${GITHUB_PROJECT}-${GITHUB_TAG}

HOMEPAGE=	https://github.com/0x7ff/gaster
COMMENT=	Checkm8 exploit that puts Apple A5-A11 devices into PwnedDFU
LICENSE=	apache-2.0

USE_LANGUAGES=	c

# Upstream generates these with xxd at build time; ship them so the
# package builds without a vim dependency on the build host.
GASTER_PAYLOADS=	payload_A9 payload_notA9 payload_notA9_armv7 \
			payload_handle_checkm8_request \
			payload_handle_checkm8_request_armv7

do-build:
.  for payload in ${GASTER_PAYLOADS}
	cd ${WRKSRC} && ${CP} ${FILESDIR}/${payload}.h .
.  endfor
	cd ${WRKSRC} && ${CC} ${CFLAGS} ${CPPFLAGS} -DHAVE_LIBUSB -I. \
		gaster.c lzfse.c -o gaster ${LDFLAGS} -lusb-1.0 -lcrypto

do-install:
	${INSTALL_PROGRAM_DIR} ${DESTDIR}${PREFIX}/bin
	${INSTALL_PROGRAM} ${WRKSRC}/gaster ${DESTDIR}${PREFIX}/bin/gaster

.include "../../devel/libusb1/buildlink3.mk"
.include "../../security/openssl/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

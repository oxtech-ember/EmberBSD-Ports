# $NetBSD$
DISTNAME= libsrtp-2.8.1
CATEGORIES= security
MASTER_SITES= ${MASTER_SITE_GITHUB:=cisco/}
GITHUB_TAG= v${PKGVERSION_NOREV}
HOMEPAGE= https://github.com/cisco/libsrtp/
COMMENT= Secure real-time transport protocol library
LICENSE= modified-bsd
USE_LANGUAGES= c
CMAKE_CONFIGURE_ARGS+= -DBUILD_SHARED_LIBS=ON -DLIBSRTP_TEST_APPS=OFF
CMAKE_CONFIGURE_ARGS+= -DENABLE_OPENSSL=ON -DENABLE_WARNINGS_AS_ERRORS=OFF
.include "../../security/openssl/buildlink3.mk"
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"

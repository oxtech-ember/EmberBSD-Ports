# $NetBSD: options.mk,v 1.9 2026/08/06 16:04:27 wiz Exp $

PKG_OPTIONS_VAR=		PKG_OPTIONS.libssh
PKG_SUPPORTED_OPTIONS=		gssapi tests
PKG_OPTIONS_REQUIRED_GROUPS=	crypto
PKG_OPTIONS_GROUP.crypto=	openssl libgcrypt
PKG_SUGGESTED_OPTIONS=		gssapi openssl

_LIBSSH_ABI_REVISION.aarch64=	3
_LIBSSH_ABI_REVISION.x86_64=	2

.include "../../mk/bsd.options.mk"

# Several supported base images expose a different OpenSSL SONAME.
.if !empty(PKG_OPTIONS:Mopenssl) && ${OPSYS} == "NetBSD" && (${MACHINE_ARCH} == "aarch64" || ${MACHINE_ARCH} == "x86_64")
PKGREVISION=	${_LIBSSH_ABI_REVISION.${MACHINE_ARCH}}
PREFER.openssl=	pkgsrc
BUILDLINK_ABI_DEPENDS.openssl+=	openssl>=4.1.0
.endif

.if !empty(PKG_OPTIONS:Mgssapi)
CMAKE_CONFIGURE_ARGS+=		-DWITH_GSSAPI:BOOL=ON
.include "../../mk/krb5.buildlink3.mk"
.if ${USE_CROSS_COMPILE:U:tl} == "yes" && ${OPSYS} == "NetBSD" && (${MACHINE_ARCH} == "aarch64" || ${MACHINE_ARCH} == "x86_64") && ${KRB5_TYPE} == "heimdal" && ${USE_BUILTIN.heimdal:Uyes:tl} == "no"
# The host krb5-config can describe MIT while the target provides Heimdal.
PKGREVISION=	${_LIBSSH_ABI_REVISION.${MACHINE_ARCH}}
BUILDLINK_FILES.heimdal+=	bin/krb5-config
CMAKE_CONFIGURE_ARGS+=	-DKRB5_CONFIG:FILEPATH=${BUILDLINK_DIR}/bin/krb5-config
CMAKE_CONFIGURE_ARGS+=	-DGSSAPI_FLAVOR_HEIMDAL:BOOL=ON
CMAKE_CONFIGURE_ARGS+=	-DGSSAPI_INCLUDE_DIR:PATH=${BUILDLINK_DIR}/${BUILDLINK_INCDIRS.heimdal:[1]}
.endif
.else
CMAKE_CONFIGURE_ARGS+=		-DWITH_GSSAPI:BOOL=OFF
.endif

.if !empty(PKG_OPTIONS:Mopenssl)
CMAKE_CONFIGURE_ARGS+=		-DWITH_GCRYPT:BOOL=OFF
BUILDLINK_API_DEPENDS.openssl+=	openssl>=3.5.0
.include "../../security/openssl/buildlink3.mk"
.endif

.if !empty(PKG_OPTIONS:Mlibgcrypt)
BUILDLINK_API_DEPENDS.libgcrypt+=	libgcrypt>=1.4
CMAKE_CONFIGURE_ARGS+=		-DWITH_GCRYPT:BOOL=ON
.include "../../security/libgcrypt/buildlink3.mk"
.endif

.if !empty(PKG_OPTIONS:Mtests)
BUILDLINK_DEPMETHOD.cmocka=	build
.include "../../devel/cmocka/buildlink3.mk"
CMAKE_CONFIGURE_ARGS+=		-DUNIT_TESTING=ON
.else
CMAKE_CONFIGURE_ARGS+=		-DUNIT_TESTING=OFF
.endif

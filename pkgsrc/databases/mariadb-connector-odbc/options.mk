# $NetBSD$
# Origin: EmberBSD (AI-assisted); driver manager choice, as in myodbc.

PKG_OPTIONS_VAR=		PKG_OPTIONS.mariadb-connector-odbc
PKG_OPTIONS_REQUIRED_GROUPS=	dm
PKG_OPTIONS_GROUP.dm=		iodbc unixodbc
PKG_SUGGESTED_OPTIONS=		unixodbc

.include "../../mk/bsd.options.mk"

.if !empty(PKG_OPTIONS:Miodbc)
.  include "../../databases/iodbc/buildlink3.mk"
CMAKE_CONFIGURE_ARGS+=	-DWITH_IODBC=ON
CMAKE_CONFIGURE_ARGS+=	-DODBC_INCLUDE_DIR=${BUILDLINK_PREFIX.iodbc}/include/iodbc
CMAKE_CONFIGURE_ARGS+=	-DODBC_LIB_DIR=${BUILDLINK_PREFIX.iodbc}/lib/iodbc
.endif

.if !empty(PKG_OPTIONS:Munixodbc)
.  include "../../databases/unixodbc/buildlink3.mk"
CMAKE_CONFIGURE_ARGS+=	-DWITH_IODBC=OFF
CMAKE_CONFIGURE_ARGS+=	-DODBC_INCLUDE_DIR=${BUILDLINK_PREFIX.unixodbc}/include
CMAKE_CONFIGURE_ARGS+=	-DODBC_LIB_DIR=${BUILDLINK_PREFIX.unixodbc}/lib
.endif

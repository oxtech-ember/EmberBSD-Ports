# $NetBSD$
# Origin: EmberBSD (AI-assisted); MariaDB Connector/ODBC replaces myodbc.

DISTNAME=	mariadb-connector-odbc-3.2.10-src
PKGNAME=	${DISTNAME:S/-src//}
CATEGORIES=	databases
MASTER_SITES=	https://archive.mariadb.org/connector-odbc-${PKGVERSION_NOREV}/

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://mariadb.com/docs/connectors/mariadb-connector-odbc/
COMMENT=	ODBC driver for MariaDB and MySQL servers
LICENSE=	gnu-lgpl-v2.1

USE_LANGUAGES=	c c++

.include "../../devel/cmake/build.mk"

# Link the one MySQL client library, MariaDB Connector/C from
# mariadb118-client. The tarball has no Connector/C copy, and the upstream
# lookup only searches /usr for libmariadb.so, so name the library (a STRING,
# so CMake links -lmariadb instead of resolving a path) and the header.
CMAKE_CONFIGURE_ARGS+=	-DMARIADB_LINK_DYNAMIC=ON
CMAKE_CONFIGURE_ARGS+=	-DUSE_SYSTEM_INSTALLED_LIB=ON
CMAKE_CONFIGURE_ARGS+=	-DCCLIB:STRING=mariadb
CMAKE_CONFIGURE_ARGS+=	-DCCHEADER=${BUILDLINK_PREFIX.mysql-client}/include/mysql/mysql.h
CMAKE_CONFIGURE_ARGS+=	-DINSTALL_LAYOUT=DEFAULT
CMAKE_CONFIGURE_ARGS+=	-DINSTALL_LIBDIR=lib
CMAKE_CONFIGURE_ARGS+=	-DINSTALL_PCDIR=lib/pkgconfig
CMAKE_CONFIGURE_ARGS+=	-DINSTALL_DOCDIR=share/doc/mariadb-connector-odbc
CMAKE_CONFIGURE_ARGS+=	-DINSTALL_LICENSEDIR=share/doc/mariadb-connector-odbc
CMAKE_CONFIGURE_ARGS+=	-DWITH_UNIT_TESTS=OFF

.include "options.mk"

.include "../../mk/mysql.buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
